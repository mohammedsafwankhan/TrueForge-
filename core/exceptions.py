"""
Custom Exception Hierarchy for Stranger Builds 2026 Agent.
"""


class StrangerAgentError(Exception):
    """Base exception for all Stranger Builds agent errors."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class ConfigurationError(StrangerAgentError):
    """Raised when agent configuration is invalid or missing required values."""


class InvalidMessageError(StrangerAgentError):
    """Raised when an incoming message is malformed, invalid, or unsupported."""


class DuplicateMessageError(StrangerAgentError):
    """Raised when a message with an already-processed msg_id is encountered."""


class SessionError(StrangerAgentError):
    """Base exception for session management issues."""


class SessionNotFoundError(SessionError):
    """Raised when an operation targets a non-existent or expired session."""


class SessionClosedError(SessionError):
    """Raised when receiving messages for an already closed session."""


class ProtocolVerificationError(StrangerAgentError):
    """Raised when an agent protocol fails manifest verification."""


class AgentverseError(StrangerAgentError):
    """Base exception for Agentverse communication and registration failures."""


class AgentverseCredentialMissingError(AgentverseError):
    """Raised when Agentverse operations require credentials that are not configured."""


# Phase 2: ASI-1 and Multi-Agent Exceptions
class ASI1ServiceError(StrangerAgentError):
    """Base exception for ASI-1 reasoning model errors."""


class ASI1AuthenticationError(ASI1ServiceError):
    """Raised when ASI-1 API key is missing, unauthorized, or rejected."""


class WorkflowExecutionError(StrangerAgentError):
    """Raised when LangGraph multi-agent execution encounters an unrecoverable failure."""


class VerificationFailedError(StrangerAgentError):
    """Raised by the Verification Agent when task execution fails quality or safety checks."""


class ToolExecutionError(StrangerAgentError):
    """Base exception for external API or MCP tool execution failures."""


class ToolNotFoundError(ToolExecutionError):
    """Raised when a delegated tool is not found in the tool registry."""


class ToolPermissionDeniedError(ToolExecutionError):
    """Raised when an operation requires approval or violates tool security policy."""
