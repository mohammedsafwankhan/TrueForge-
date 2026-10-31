"""
Stranger Builds 2026 - Phase 1 Primary Agent Entry Point.
Launches the autonomous agent with the official Fetch.ai Chat Protocol.
"""

import sys

from agents.primary_agent import create_primary_agent, get_agent_details
from core.config import get_settings
from core.logger import setup_logger


def main() -> None:
    """Initialize and run the primary agent."""
    settings = get_settings()
    logger = setup_logger(level=settings.LOG_LEVEL)

    logger.info("Initializing Stranger Builds 2026 Primary Agent...")
    agent = create_primary_agent(settings=settings)

    details = get_agent_details(agent)
    logger.info(f"Agent Initialized: {details['name']} -> {details['address']}")
    logger.info(f"Wallet Address   : {details['wallet_address']}")
    logger.info(f"Registered Protos: {details['protocols']}")

    logger.info("Starting agent event loop...")
    try:
        agent.run()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Agent process terminated by user.")
    except Exception as exc:
        logger.exception(f"Unexpected fatal error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
