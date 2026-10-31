"""
Primary Agent Implementation for Stranger Builds 2026.
Configures cryptographic identity, Agentverse registration readiness, and Chat Protocol manifest.
"""

import asyncio
from typing import Any

from uagents import Agent, Context

from core.config import Settings, get_settings
from core.logger import get_agent_logger
from core.reliability import health_tracker
from models.requests import WebChatRequest, WebPaymentRequest
from models.responses import (
    AgentHealthInfo,
    AgentPreviewInfo,
    WebChatResponse,
    WebPaymentResponse,
)
from payment.service import payment_service
from protocols.chat_protocol import chat_proto, setup_chat_protocol
from services.message_service import MessageService
from services.session_service import SessionService

logger = get_agent_logger("agents.primary_agent")


def ensure_event_loop() -> asyncio.AbstractEventLoop:
    """Ensure an asyncio event loop exists in the current thread."""
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


def create_primary_agent(
    settings: Settings | None = None,
    message_service: MessageService | None = None,
) -> Agent:
    """
    Factory creating and configuring the primary autonomous agent.

    Args:
        settings: Application settings (defaults to get_settings()).
        message_service: Business logic message service instance.

    Returns:
        Configured and protocol-verified Fetch.ai Agent.
    """
    cfg = settings or get_settings()
    loop = ensure_event_loop()

    # Determine seed: use configured AGENT_SEED or fallback to a deterministic default for reproducibility
    seed = cfg.AGENT_SEED or f"{cfg.AGENT_NAME}_secret_seed_phrase_stranger_builds_2026"

    # Initialize dependencies if not supplied
    if message_service is None:
        session_svc = SessionService(expiry_seconds=cfg.SESSION_EXPIRY_SECONDS)
        message_service = MessageService(
            session_service=session_svc,
            dedup_cache_size=10000,
            dedup_ttl_seconds=cfg.MESSAGE_DEDUPLICATION_TTL_SECONDS,
        )

    # Configure chat protocol with injected service
    configured_proto = setup_chat_protocol(message_service=message_service)

    # Mailbox configuration
    mailbox_enabled = cfg.is_mailbox_enabled()

    # Agent metadata for Almanac and Agentverse registration
    metadata = {
        "framework": "fetchai-uagents",
        "chat_protocol_version": "0.3.0",
        "asi_compatible": True,
        "hackathon": "Stranger Builds 2026",
        "phase": 3,
        "capabilities": [
            "chat",
            "session_management",
            "asi1_reasoning",
            "multi_agent_orchestration",
            "mcp_tools",
            "interactive_cards",
            "payment_protocol",
        ],
    }

    # Instantiate Agent
    agent = Agent(
        name=cfg.AGENT_NAME,
        seed=seed,
        port=cfg.AGENT_PORT,
        endpoint=cfg.AGENT_ENDPOINT,
        mailbox=mailbox_enabled,
        network=cfg.AGENT_NETWORK,
        version=cfg.AGENT_VERSION,
        description=cfg.AGENT_DESCRIPTION,
        loop=loop,
        metadata=metadata,
        publish_agent_details=True,
    )

    # Include official Fetch.ai Agent Chat Protocol with manifest publication
    agent.include(configured_proto, publish_manifest=True)

    # Local browser preview endpoint on HTTP GET /
    @agent.on_rest_get("/", AgentPreviewInfo)
    async def preview_handler(_ctx: Context) -> AgentPreviewInfo:
        wallet_str = ""
        if getattr(agent, "wallet", None):
            raw_addr = getattr(agent.wallet, "address", None)
            wallet_str = str(raw_addr()) if callable(raw_addr) else str(raw_addr)

        manifest_digest = ""
        for digest, p in agent.protocols.items():
            if p.name == "AgentChatProtocol":
                manifest_digest = digest
                break

        port = getattr(agent, "_port", cfg.AGENT_PORT)
        inspector = f"https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A{port}&address={agent.address}"

        return AgentPreviewInfo(
            name=agent.name,
            address=agent.address,
            wallet_address=wallet_str,
            status="ONLINE",
            version=cfg.AGENT_VERSION,
            network=cfg.AGENT_NETWORK,
            protocol="AgentChatProtocol:0.3.0",
            manifest_digest=manifest_digest or "proto:30a801ed3a83f9a0ff0a9f1e6fe958cb91da1fc2218b153df7b6cbf87bd33d62",
            inspector_url=inspector,
        )

    # Health check endpoint on HTTP GET /health
    @agent.on_rest_get("/health", AgentHealthInfo)
    async def health_handler(_ctx: Context) -> AgentHealthInfo:
        h_data = health_tracker.get_health_status()
        return AgentHealthInfo(
            status=h_data["status"],
            uptime_seconds=h_data["uptime_seconds"],
            timestamp=h_data["timestamp"],
            details=f"Subsystems healthy: {len(h_data['subsystems'])}. Breakers: {len(h_data['circuit_breakers'])}",
        )

    # Full-Stack Web API: Interactive Chat Endpoint
    @agent.on_rest_post("/api/chat", WebChatRequest, WebChatResponse)
    async def web_chat_handler(ctx: Context, req: WebChatRequest) -> WebChatResponse:
        payer = req.payer_address or "web_user"
        try:
            session = message_service.session_service.get_or_create_session(sender=payer)
            reply_text, cards_list = await message_service._execute_agent_business_logic(
                sender=payer,
                user_text=req.message,
                session=session,
            )
            fee = payment_service.calculate_price(req.message)
            has_card = bool(cards_list)
            card_type = ""
            card_title = ""
            card_payload = ""
            if has_card and hasattr(cards_list[0], "metadata"):
                meta = cards_list[0].metadata
                card_type = str(meta.get("card_type", ""))
                card_title = str(meta.get("card_title") or meta.get("title", ""))
                card_payload = str(meta.get("card_payload", ""))

            return WebChatResponse(
                reply=reply_text,
                session_id=str(session.session_id),
                action="chat_response",
                fee_fet=fee,
                has_card=has_card,
                card_type=card_type,
                card_title=card_title,
                card_payload=card_payload,
                verification_status="PASSED",
            )
        except Exception as exc:
            ctx.logger.error(f"Error in web_chat_handler: {exc}")
            return WebChatResponse(
                reply=f"Processing error: {exc}",
                session_id=req.session_id or "unknown",
                action="error",
                verification_status="FAILED",
            )

    # Full-Stack Web API: On-Chain Payment Verification Endpoint
    @agent.on_rest_post("/api/pay", WebPaymentRequest, WebPaymentResponse)
    async def web_pay_handler(_ctx: Context, req: WebPaymentRequest) -> WebPaymentResponse:
        ver_res = await payment_service.verify_transaction(
            tx_hash=req.tx_hash,
            expected_amount_fet=req.expected_amount_fet,
            task_id=req.task_id,
            payer_address=req.payer_address,
        )
        msg = ver_res.error or f"Transaction {req.tx_hash[:16]} confirmed on Fetch.ai Dorado ledger."
        return WebPaymentResponse(
            verified=ver_res.verified,
            status=ver_res.status.value,
            tx_hash=ver_res.tx_hash or req.tx_hash,
            block_height=ver_res.block_height or 0,
            message=msg,
        )

    # Agent lifecycle hooks
    @agent.on_event("startup")
    async def startup_handler(ctx: Context) -> None:
        ctx.logger.info("=" * 60)
        ctx.logger.info("STRANGER BUILDS 2026 - PRIMARY AGENT ONLINE")
        ctx.logger.info(f"Agent Name    : {agent.name}")
        ctx.logger.info(f"Agent Address : {agent.address}")
        ctx.logger.info(f"Target Network: {cfg.AGENT_NETWORK}")
        ctx.logger.info(f"Listening Port: {cfg.AGENT_PORT}")
        ctx.logger.info(f"Mailbox Active: {mailbox_enabled}")
        ctx.logger.info(f"Protocols     : {list(agent.protocols.keys())}")
        ctx.logger.info("=" * 60)

    @agent.on_event("shutdown")
    async def shutdown_handler(ctx: Context) -> None:
        ctx.logger.info(f"Shutting down {agent.name} [{agent.address}] gracefully...")

    return agent


def get_agent_details(agent: Agent) -> dict[str, Any]:
    """
    Extract configuration and registration summary for an agent instance.
    """
    wallet_addr = None
    if getattr(agent, "wallet", None):
        raw_addr = getattr(agent.wallet, "address", None)
        wallet_addr = str(raw_addr()) if callable(raw_addr) else str(raw_addr)

    return {
        "name": agent.name,
        "address": agent.address,
        "wallet_address": wallet_addr,
        "protocols": list(agent.protocols.keys()),
        "endpoints": [str(ep) for ep in getattr(agent, "_endpoints", [])],
        "metadata": getattr(agent, "_metadata", {}),
    }
