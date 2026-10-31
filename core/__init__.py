"""
Core package for Stranger Builds 2026 Primary Agent.
Contains configuration, logging, and custom exception definitions.
"""

from .config import Settings, get_settings
from .exceptions import (
    AgentverseCredentialMissingError,
    AgentverseError,
    ConfigurationError,
    DuplicateMessageError,
    InvalidMessageError,
    ProtocolVerificationError,
    SessionClosedError,
    SessionError,
    SessionNotFoundError,
    StrangerAgentError,
)
from .logger import get_agent_logger, setup_logger

__all__ = [
    "Settings",
    "get_settings",
    "StrangerAgentError",
    "ConfigurationError",
    "InvalidMessageError",
    "DuplicateMessageError",
    "SessionError",
    "SessionNotFoundError",
    "SessionClosedError",
    "ProtocolVerificationError",
    "AgentverseError",
    "AgentverseCredentialMissingError",
    "setup_logger",
    "get_agent_logger",
]
