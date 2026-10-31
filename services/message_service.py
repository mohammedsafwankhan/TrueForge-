"""
Message Processing Service.
Handles deduplication, content parsing, session orchestration, and business logic execution.
"""

from collections import OrderedDict
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import UUID, uuid4

from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    StartSessionContent,
    TextContent,
)

from core.exceptions import InvalidMessageError
from core.logger import get_agent_logger
from models.requests import InboundContentSummary, InboundMessageContext, SessionAction
from models.responses import AgentStructuredResponse, ExecutionResult, ResponseStatus
from services.session_service import SessionService

logger = get_agent_logger("services.message_service")


class DeduplicationCache:
    """
    LRU and TTL-based deduplication registry for message IDs.
    Ensures exactly-once processing of agent messages.
    """

    def __init__(self, max_size: int = 10000, ttl_seconds: int = 3600) -> None:
        self._cache: OrderedDict[UUID, float] = OrderedDict()
        self._max_size: int = max_size
        self._ttl_seconds: float = float(ttl_seconds)
        self._lock: Lock = Lock()

    def is_duplicate(self, msg_id: UUID) -> bool:
        """Check if message ID is known and not expired."""
        with self._lock:
            now = datetime.now(timezone.utc).timestamp()
            if msg_id in self._cache:
                timestamp = self._cache[msg_id]
                if now - timestamp <= self._ttl_seconds:
                    # Move to end (most recently accessed)
                    self._cache.move_to_end(msg_id)
                    return True
                else:
                    # Expired entry
                    del self._cache[msg_id]
            return False

    def mark_processed(self, msg_id: UUID) -> None:
        """Record message ID as processed."""
        with self._lock:
            now = datetime.now(timezone.utc).timestamp()
            self._cache[msg_id] = now
            self._cache.move_to_end(msg_id)

            # Evict oldest if exceeding max_size
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def clear(self) -> None:
        """Clear the cache (primarily for test resets)."""
        with self._lock:
            self._cache.clear()


class MessageService:
    """
    Core business service for processing incoming Chat Protocol messages.
    Maintains clean decoupling between network transport and application logic.
    """

    def __init__(
        self,
        session_service: SessionService,
        dedup_cache_size: int = 10000,
        dedup_ttl_seconds: int = 3600,
    ) -> None:
        self.session_service = session_service
        self.dedup_cache = DeduplicationCache(
            max_size=dedup_cache_size,
            ttl_seconds=dedup_ttl_seconds,
        )

    def create_acknowledgement(self, msg_id: UUID) -> ChatAcknowledgement:
        """
        Construct a compliant ChatAcknowledgement with a timezone-aware UTC timestamp.
        """
        return ChatAcknowledgement(
            timestamp=datetime.now(timezone.utc),
            acknowledged_msg_id=msg_id,
            metadata=None,
        )

    def parse_inbound_message(self, sender: str, msg: ChatMessage) -> InboundMessageContext:
        """
        Validate and extract domain-level context from a ChatMessage.

        Raises:
            InvalidMessageError: When msg or its content is malformed.
        """
        if not msg:
            raise InvalidMessageError("Received null or empty ChatMessage object.")

        if not getattr(msg, "msg_id", None):
            raise InvalidMessageError("ChatMessage missing required 'msg_id' field.")

        if not getattr(msg, "timestamp", None):
            raise InvalidMessageError("ChatMessage missing required 'timestamp' field.")

        # Ensure timezone-aware timestamp
        ts = msg.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        content_list = getattr(msg, "content", None)
        if content_list is None or not isinstance(content_list, list):
            raise InvalidMessageError("ChatMessage 'content' must be a valid list.")

        extracted_text: list[str] = []
        raw_types: list[str] = []
        session_action = SessionAction.NONE

        for item in content_list:
            if isinstance(item, StartSessionContent):
                session_action = SessionAction.START
                raw_types.append("start-session")
            elif isinstance(item, EndSessionContent):
                session_action = SessionAction.END
                raw_types.append("end-session")
            elif isinstance(item, TextContent):
                raw_types.append("text")
                if item.text and item.text.strip():
                    extracted_text.append(item.text.strip())
            elif getattr(item, "type", "") == "metadata" and hasattr(item, "metadata"):
                raw_types.append("metadata")
                meta_dict = getattr(item, "metadata", {}) or {}
                # Capture action or form submissions
                if "action_id" in meta_dict:
                    extracted_text.append(f"action:{meta_dict['action_id']}")
            else:
                # Handle generic or duck-typed content models
                item_type = getattr(item, "type", "unknown")
                raw_types.append(item_type)
                if item_type == "text" and hasattr(item, "text"):
                    extracted_text.append(str(item.text).strip())
                elif item_type == "start-session":
                    session_action = SessionAction.START
                elif item_type == "end-session":
                    session_action = SessionAction.END

        return InboundMessageContext(
            sender=sender,
            msg_id=msg.msg_id,
            timestamp=ts,
            session_action=session_action,
            extracted_text=extracted_text,
            raw_content_types=raw_types,
        )

    async def process_message(
        self,
        sender: str,
        msg: ChatMessage,
    ) -> tuple[ChatAcknowledgement, ChatMessage | None, AgentStructuredResponse]:
        """
        Main entry point for ChatMessage handling:
        1. Generates immediate ChatAcknowledgement.
        2. Validates incoming message.
        3. Enforces deduplication.
        4. Identifies and manages session boundaries.
        5. Executes business logic and generates structured response.
        6. Constructs outbound ChatMessage if applicable.

        Returns:
            Tuple of (ChatAcknowledgement, Optional[ChatMessage reply], AgentStructuredResponse domain model).
        """
        # Step 1: Immediate acknowledgement generation
        ack = self.create_acknowledgement(msg.msg_id)

        # Step 2: Validation & Context Extraction
        try:
            inbound_context = self.parse_inbound_message(sender, msg)
        except InvalidMessageError as err:
            logger.error(f"Message validation failed for sender {sender}: {err}")
            error_response = AgentStructuredResponse(
                status=ResponseStatus.ERROR,
                sender_address=sender,
                reply_text=f"Error: Invalid message format - {err.message}",
                execution_result=ExecutionResult(
                    success=False,
                    action_performed="validation_failed",
                    error_message=err.message,
                ),
            )
            # Create error ChatMessage
            reply_msg = ChatMessage(
                timestamp=datetime.now(timezone.utc),
                msg_id=uuid4(),
                content=[TextContent(type="text", text=error_response.reply_text or "Error")],
            )
            return ack, reply_msg, error_response

        # Step 3: Duplicate detection
        if self.dedup_cache.is_duplicate(inbound_context.msg_id):
            logger.warning(
                f"Duplicate message ignored: msg_id={inbound_context.msg_id} from sender {sender}"
            )
            dup_response = AgentStructuredResponse(
                status=ResponseStatus.IGNORED_DUPLICATE,
                sender_address=sender,
                reply_text=None,
                execution_result=ExecutionResult(
                    success=True,
                    action_performed="deduplication_drop",
                    details={"msg_id": str(inbound_context.msg_id)},
                ),
            )
            return ack, None, dup_response

        # Mark as processed in deduplication registry
        self.dedup_cache.mark_processed(inbound_context.msg_id)

        # Step 4: Handle Session Boundaries
        session = None
        reply_content_blocks = []
        structured_response: AgentStructuredResponse

        if inbound_context.session_action == SessionAction.START:
            session = self.session_service.start_session(sender)
            logger.info(f"Initialized dialogue session {session.session_id} for sender {sender}")

            reply_text = (
                f"Session initialized [ID: {session.session_id}]. "
                "Stranger Builds 2026 Primary Agent ready for instructions."
            )
            if inbound_context.extracted_text:
                # User sent initial instructions alongside StartSessionContent
                additional_resp, additional_cards = await self._execute_agent_business_logic(
                    sender=sender,
                    user_text=inbound_context.combined_text,
                    session=session,
                )
                reply_text += f"\n\n{additional_resp}"
                for card in additional_cards:
                    reply_content_blocks.append(card)

            structured_response = AgentStructuredResponse(
                status=ResponseStatus.SESSION_STARTED,
                sender_address=sender,
                session_id=session.session_id,
                reply_text=reply_text,
                execution_result=ExecutionResult(
                    success=True,
                    action_performed="session_start",
                    details={"session_id": str(session.session_id)},
                ),
            )
            reply_content_blocks.append(TextContent(type="text", text=reply_text))

        elif inbound_context.session_action == SessionAction.END:
            ended_session = self.session_service.end_session(sender)
            s_id = ended_session.session_id if ended_session else None
            reply_text = f"Session {s_id} successfully terminated. Thank you."
            structured_response = AgentStructuredResponse(
                status=ResponseStatus.SESSION_ENDED,
                sender_address=sender,
                session_id=s_id,
                reply_text=reply_text,
                execution_result=ExecutionResult(
                    success=True,
                    action_performed="session_end",
                    details={"session_id": str(s_id) if s_id else None},
                ),
            )
            reply_content_blocks.append(EndSessionContent(type="end-session"))
            reply_content_blocks.append(TextContent(type="text", text=reply_text))

        else:
            # Normal conversational message or multi-text block request
            session = self.session_service.get_or_create_session(sender)

            if inbound_context.extracted_text:
                combined_query = inbound_context.combined_text
                reply_text, cards = await self._execute_agent_business_logic(
                    sender=sender,
                    user_text=combined_query,
                    session=session,
                )
                structured_response = AgentStructuredResponse(
                    status=ResponseStatus.PROCESSED,
                    sender_address=sender,
                    session_id=session.session_id,
                    reply_text=reply_text,
                    execution_result=ExecutionResult(
                        success=True,
                        action_performed="request_processed",
                        details={"blocks_processed": len(inbound_context.extracted_text), "cards_attached": len(cards)},
                    ),
                )
                reply_content_blocks.append(TextContent(type="text", text=reply_text))
                for card in cards:
                    reply_content_blocks.append(card)
            else:
                # Message received without recognizable text content
                reply_text = "Received message with no text content."
                structured_response = AgentStructuredResponse(
                    status=ResponseStatus.PROCESSED,
                    sender_address=sender,
                    session_id=session.session_id,
                    reply_text=reply_text,
                    execution_result=ExecutionResult(
                        success=True,
                        action_performed="empty_content_processed",
                    ),
                )
                reply_content_blocks.append(TextContent(type="text", text=reply_text))

        # Record interaction in session history if active
        if session and session.is_active():
            session.record_interaction(
                msg_id=inbound_context.msg_id,
                direction="inbound",
                summary=inbound_context.combined_text or "[session boundary event]",
            )
            if structured_response.reply_text:
                session.record_interaction(
                    msg_id=uuid4(),
                    direction="outbound",
                    summary=structured_response.reply_text,
                )

        # Build outbound ChatMessage envelope
        outbound_msg: ChatMessage | None = None
        if reply_content_blocks:
            outbound_msg = ChatMessage(
                timestamp=datetime.now(timezone.utc),
                msg_id=uuid4(),
                content=reply_content_blocks,
            )

        return ack, outbound_msg, structured_response

    async def _execute_agent_business_logic(
        self,
        sender: str,
        user_text: str,
        session: Any,
    ) -> tuple[str, list[Any]]:
        """
        Extensible business logic handler.
        Routes to LangGraph multi-agent engine with ASI-1, ASI Interactive Cards, and Payment Protocol.
        """
        import re
        from cards.card_factory import CardFactory
        from payment.service import payment_service
        from tools.api_tools import fetch_token_price

        cleaned_text = user_text.strip().lower()

        # Update context metrics in session memory
        turn_count = session.get_context("turn_count", 0) + 1
        session.set_context("turn_count", turn_count)
        session.set_context("last_query", user_text)

        # Standard built-in fast commands
        if cleaned_text == "ping":
            return f"Pong! Agent active. Session ID: {session.session_id} (Turn #{turn_count})", []

        if cleaned_text in ("status", "info"):
            status_text = (
                f"Agent Status: ONLINE\n"
                f"Session ID: {session.session_id}\n"
                f"Sender: {sender}\n"
                f"Turns recorded: {turn_count}\n"
                f"Protocol: AgentChatProtocol:0.3.0\n"
                f"Architecture: Fetch.ai uAgents + LangGraph Multi-Agent (Phase 3)\n"
                f"Reasoning Engine: ASI-1 (Connected)\n"
                f"Interactive Cards: ASI:One Dynamic UI Active\n"
                f"Payment Protocol: Fetch.ai Pay-Per-Task Active"
            )
            return status_text, []

        if cleaned_text == "help":
            help_text = (
                "Stranger Builds 2026 Autonomous Agent Capabilities:\n"
                "- 'cards' / 'services': Launch interactive selection card\n"
                "- 'form' / 'configure': Launch task parameter input form\n"
                "- 'price of <token>': Live pricing oracle with Detail Card ($FET, $ETH, $BTC)\n"
                "- 'premium analysis': Trigger pay-per-task model with Payment Review Card\n"
                "- 'pay <tx_hash>': Verify on-chain payment and execute task\n"
                "- Freeform request: Autonomous multi-agent execution with ASI-1 & Result Card"
            )
            return help_text, []

        # 1. Interactive Selection Card trigger
        if any(w in cleaned_text for w in ("cards", "menu", "services", "select")):
            card = CardFactory.create_selection_card(
                title="Select Autonomous Capability",
                description="Tap an action below to activate a specialized agent service on ASI:One:",
            )
            return "Here are the available autonomous capabilities. You can select any service below:", [card]

        # 2. Interactive Input Form Card trigger
        if any(w in cleaned_text for w in ("form", "configure", "input form")):
            card = CardFactory.create_input_form_card(
                title="Configure Autonomous Valuation Task",
                description="Specify target asset and volume to analyze:",
            )
            return "Please provide execution parameters in the input form below:", [card]

        # 3. Payment Review trigger (Pay-Per-Task model)
        if any(w in cleaned_text for w in ("premium", "invoice", "pay task")):
            task_id = str(uuid4())
            invoice = payment_service.create_invoice(
                task_id=task_id,
                task_name="Autonomous Multi-Agent Market & Valuation Task",
                payer_address=sender,
            )
            review_card = payment_service.generate_review_card(invoice)
            review_text = (
                f"This autonomous operation requires explicit payment authorization under our Pay-Per-Task model.\n"
                f"- Task ID: {task_id}\n"
                f"- Fee: {invoice.amount_fet} FET ({invoice.denom})\n"
                f"- Merchant: {invoice.merchant_wallet}\n\n"
                "Please review the invoice card below and broadcast the payment on Fetch.ai ledger:"
            )
            return review_text, [review_card]

        # 4. Payment Verification trigger
        tx_match = re.search(r"(?:pay|verify|tx|hash)\s+([0-9a-fA-F]{64})", user_text)
        if tx_match:
            tx_hash = tx_match.group(1).upper()
            verif_res = await payment_service.verify_transaction(
                tx_hash=tx_hash,
                expected_amount_fet=0.05,
                payer_address=sender,
            )
            if not verif_res.verified:
                fail_text = f"Payment Verification Failed: {verif_res.error}. Operation cancelled."
                return fail_text, []

            # Payment verified successfully!
            confirm_card = CardFactory.create_confirmation_card(
                title="Payment Confirmed On-Chain",
                message=f"Verified 0.05 FET transfer on Fetch.ai ledger.",
                tx_hash=tx_hash,
            )
            # Proceed to autonomous task execution
            from orchestration.engine import get_orchestration_engine

            engine = get_orchestration_engine()
            task_result = await engine.execute_task(
                user_request="Autonomous Market Valuation Task",
                session_id=str(session.session_id),
                sender=sender,
            )
            result_card = CardFactory.create_result_card(
                title="Execution Results",
                summary="Autonomous execution completed following verified ledger settlement.",
                data={"status": "completed", "tx_hash": tx_hash, "verification": "passed"},
                verification_passed=True,
            )
            return task_result.get("final_response") or "Task executed successfully.", [confirm_card, result_card]

        # 5. Detail Card for Token Pricing
        if "price of" in cleaned_text or "fet price" in cleaned_text or "token price" in cleaned_text:
            token = "fetch-ai"
            if "eth" in cleaned_text:
                token = "ethereum"
            elif "btc" in cleaned_text:
                token = "bitcoin"

            price_info = await fetch_token_price(token_id=token)
            if "price" in price_info:
                detail_card = CardFactory.create_detail_card(
                    title=f"{token.upper()} Market Telemetry",
                    description="Verified live pricing oracle feed:",
                    details={
                        "asset": token,
                        "price_usd": f"${price_info.get('price'):.4f}",
                        "24h_change": f"{price_info.get('change_24h_percent'):.2f}%",
                        "oracle": price_info.get("oracle"),
                    },
                    source="CoinGecko API",
                )
                text_resp = f"The live price of {token.upper()} is ${price_info.get('price'):.4f} USD ({price_info.get('change_24h_percent'):.2f}% in 24h)."
                return text_resp, [detail_card]

        # 6. Autonomous Multi-Agent LangGraph Execution Pipeline with Result Card
        try:
            from orchestration.engine import get_orchestration_engine

            engine = get_orchestration_engine()
            task_result = await engine.execute_task(
                user_request=user_text,
                session_id=str(session.session_id),
                sender=sender,
            )
            final_text = (
                task_result.get("final_response")
                or f"[Stranger Builds Agent | Session {session.session_id}] Completed turn #{turn_count}."
            )
            is_valid = task_result.get("verification", {}).get("is_valid", True)
            result_card = CardFactory.create_result_card(
                title="Verified Autonomous Result",
                summary=final_text[:120] + "...",
                data={"task_id": task_result.get("task_id"), "status": task_result.get("status")},
                verification_passed=is_valid,
            )
            return final_text, [result_card]
        except Exception as exc:
            logger.warning(f"Orchestration engine fallback ({exc}). Returning turn summary.")
            return (
                f"[Stranger Builds Agent | Session {session.session_id}] "
                f"Processed turn #{turn_count}: '{user_text}'",
                [],
            )
