"""
Agents Package for Stranger Builds 2026.
Contains primary agent definitions and lifecycle factories.
"""

from .primary_agent import create_primary_agent, get_agent_details

__all__ = ["create_primary_agent", "get_agent_details"]
