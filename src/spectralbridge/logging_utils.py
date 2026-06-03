"""Small helpers for package and CLI logging setup."""

from __future__ import annotations

import logging


def configure_cli_logging(level: int = logging.INFO) -> None:
    """Configure root logging for CLI entry points when needed.

    ``logging.basicConfig`` is intentionally called only when the root logger
    has no handlers so notebook sessions and embedding applications keep control
    of their own logging configuration.
    """

    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(level=level)
