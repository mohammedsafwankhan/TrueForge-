"""
Protocols Package for Stranger Builds 2026 Primary Agent.
Hosts Fetch.ai standard communication protocols including the official Chat Protocol.
"""

from .chat_protocol import chat_proto, setup_chat_protocol

__all__ = ["chat_proto", "setup_chat_protocol"]
