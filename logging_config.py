"""Logging configuration for MagnitSearch."""

import logging
import sys


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Configure and return a logger with consistent formatting.

    Args:
        name: Logger name (typically __name__ from calling module).
        level: Logging level (default INFO).

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(
            fmt="%(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
