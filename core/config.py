"""
Configuration Management for Stranger Builds 2026 Primary Agent.
Loads configuration from environment variables and .env files with validation.
"""

import os
from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables from .env file if present
load_dotenv()


class Settings(BaseModel):
    """
    Application Settings for Stranger Builds Primary Agent.
    """

    # Agent Identity & Network
    AGENT_NAME: str = Field(
        default_factory=lambda: os.getenv("AGENT_NAME", "stranger_builds_primary_agent"),
        description="Fetch.ai agent logical identifier",
    )
    AGENT_SEED: str | None = Field(
        default_factory=lambda: os.getenv("AGENT_SEED") or None,
        description="Seed used for deterministic cryptographic address and key generation",
    )
    AGENT_PORT: int = Field(
        default_factory=lambda: int(os.getenv("AGENT_PORT", "8000")),
        description="Local HTTP listening port for incoming agent messages",
    )
    AGENT_ENDPOINT: str | None = Field(
        default_factory=lambda: os.getenv("AGENT_ENDPOINT") or None,
        description="Public webhook/endpoint URL for direct message delivery",
    )
    AGENT_NETWORK: Literal["mainnet", "testnet"] = Field(
        default_factory=lambda: os.getenv("AGENT_NETWORK", "mainnet"),  # type: ignore
        description="Target Fetch.ai / ASI network",
    )
    AGENT_VERSION: str = Field(
        default_factory=lambda: os.getenv("AGENT_VERSION", "0.1.0"),
        description="SemVer release version of the agent",
    )
    AGENT_DESCRIPTION: str = Field(
        default_factory=lambda: os.getenv(
            "AGENT_DESCRIPTION",
            "Stranger Builds 2026 Primary Autonomous Agent powered by Fetch.ai Chat Protocol",
        ),
        description="Human-readable description for Agentverse and Almanac discovery",
    )

    # Agentverse Configuration
    AGENTVERSE_API_KEY: str | None = Field(
        default_factory=lambda: os.getenv("AGENTVERSE_API_KEY") or None,
        description="Agentverse API token for programmatic registration and Mailbox provisioning",
    )
    AGENTVERSE_MAILBOX_KEY: str | None = Field(
        default_factory=lambda: os.getenv("AGENTVERSE_MAILBOX_KEY") or None,
        description="Agentverse Mailbox authentication key",
    )
    AGENTVERSE_URL: str = Field(
        default_factory=lambda: os.getenv("AGENTVERSE_URL", "https://agentverse.ai"),
        description="Base URL for Agentverse service APIs",
    )

    # Operational Parameters
    LOG_LEVEL: str = Field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper(),
        description="Logging verbosity (DEBUG, INFO, WARNING, ERROR)",
    )
    MESSAGE_DEDUPLICATION_TTL_SECONDS: int = Field(
        default_factory=lambda: int(os.getenv("MESSAGE_DEDUPLICATION_TTL_SECONDS", "3600")),
        description="Time-to-live for processed message IDs to prevent duplicate processing",
    )
    SESSION_EXPIRY_SECONDS: int = Field(
        default_factory=lambda: int(os.getenv("SESSION_EXPIRY_SECONDS", "86400")),
        description="Maximum idle duration before an active session expires (seconds)",
    )

    # Phase 2: ASI-1 Reasoning Engine
    ASI1_API_KEY: str | None = Field(
        default_factory=lambda: os.getenv("ASI1_API_KEY") or None,
        description="API Key for ASI-1 primary reasoning model",
    )
    ASI1_API_BASE: str = Field(
        default_factory=lambda: os.getenv("ASI1_API_BASE", "https://api.asi1.ai/v1"),
        description="Base URL for ASI-1 API endpoints",
    )
    ASI1_MODEL: str = Field(
        default_factory=lambda: os.getenv("ASI1_MODEL", "asi1-mini"),
        description="ASI-1 model identifier",
    )

    # Phase 2: Database & Caching
    POSTGRES_URL: str | None = Field(
        default_factory=lambda: os.getenv("POSTGRES_URL") or None,
        description="PostgreSQL database connection URL (asyncpg format)",
    )
    REDIS_URL: str | None = Field(
        default_factory=lambda: os.getenv("REDIS_URL") or None,
        description="Redis connection URL for distributed caching and state",
    )

    # Phase 2: MCP & Tool Execution
    MCP_SERVER_ENDPOINT: str | None = Field(
        default_factory=lambda: os.getenv("MCP_SERVER_ENDPOINT") or None,
        description="Model Context Protocol (MCP) server endpoint URL",
    )
    MCP_AUTH_TOKEN: str | None = Field(
        default_factory=lambda: os.getenv("MCP_AUTH_TOKEN") or None,
        description="Authentication bearer token for MCP server if required",
    )

    def is_mailbox_enabled(self) -> bool:
        """Check if Agentverse Mailbox configuration is provided."""
        return bool(self.AGENTVERSE_MAILBOX_KEY)

    def has_agentverse_credentials(self) -> bool:
        """Check if an Agentverse API key is configured."""
        return bool(self.AGENTVERSE_API_KEY)

    def has_asi1_credentials(self) -> bool:
        """Check if an ASI-1 API key is configured."""
        return bool(self.ASI1_API_KEY)

    def sanitized_dict(self) -> dict:
        """Return configuration dictionary with sensitive credentials masked."""
        data = self.model_dump()
        if data.get("AGENT_SEED"):
            data["AGENT_SEED"] = "[REDACTED_SEED]"
        if data.get("AGENTVERSE_API_KEY"):
            data["AGENTVERSE_API_KEY"] = "[REDACTED_KEY]"
        if data.get("AGENTVERSE_MAILBOX_KEY"):
            data["AGENTVERSE_MAILBOX_KEY"] = "[REDACTED_KEY]"
        if data.get("ASI1_API_KEY"):
            data["ASI1_API_KEY"] = "[REDACTED_KEY]"
        if data.get("MCP_AUTH_TOKEN"):
            data["MCP_AUTH_TOKEN"] = "[REDACTED_TOKEN]"
        return data

    def __repr__(self) -> str:
        items = [f"{k}={v!r}" for k, v in self.sanitized_dict().items()]
        return f"Settings({', '.join(items)})"

    def __str__(self) -> str:
        return self.__repr__()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retrieve cached application settings instance."""
    return Settings()
