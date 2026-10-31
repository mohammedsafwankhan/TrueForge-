"""
Structured Logger for Stranger Builds 2026 Primary Agent.
Provides redaction of sensitive credentials and unified formatting.
"""

import logging
import re
import sys
from typing import Any

# Sensitive pattern regexes for sanitization
SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(api[-_]?key\s*[:=]\s*)(['\"])?([a-zA-Z0-9_\-]{8,})(['\"])?"),
    re.compile(r"(?i)(seed\s*[:=]\s*)(['\"])?([a-zA-Z0-9_\-\s]{12,})(['\"])?"),
    re.compile(r"(?i)(bearer\s+)([a-zA-Z0-9_\-\.]{10,})"),
    re.compile(r"(?i)(private[-_]?key\s*[:=]\s*)(['\"])?([a-zA-Z0-9_\-]{16,})(['\"])?"),
]


class SensitiveDataFilter(logging.Filter):
    """
    Log filter that masks sensitive values (tokens, seeds, API keys) from log messages.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self._sanitize(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._sanitize_value(v) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._sanitize_value(v) for v in record.args)
        return True

    def _sanitize_value(self, value: Any) -> Any:
        if isinstance(value, str):
            return self._sanitize(value)
        return value

    def _sanitize(self, text: str) -> str:
        sanitized = text
        for pattern in SENSITIVE_PATTERNS:
            sanitized = pattern.sub(
                r"\1\2[REDACTED]\4" if pattern.groups >= 4 else r"\1[REDACTED]",
                sanitized,
            )
        return sanitized


def setup_logger(
    name: str = "stranger_builds",
    level: str = "INFO",
) -> logging.Logger:
    """
    Configure and return a structured logger with security filtering.

    Args:
        name: Logger name.
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    # Avoid duplicate handlers if already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(numeric_level)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | [%(name)s] %(filename)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(SensitiveDataFilter())
        logger.addHandler(handler)

    logger.propagate = False
    return logger


def get_agent_logger(name: str = "stranger_builds") -> logging.Logger:
    """
    Retrieve or create an agent logger instance.
    """
    return setup_logger(name)
