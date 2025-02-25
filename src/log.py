"""Shared logging configuration for the application."""

import os
import logging
from logging.handlers import RotatingFileHandler

# Configure default log directory
LOG_DIR = os.environ.get("LOG_DIR", "logs")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.environ.get("LOG_FILE", "app.log")
LOG_FORMAT = "ClaudeCodeBot - %(asctime)s - %(levelname)s - %(message)s"

# Create logs directory if it doesn't exist
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Map string log levels to their corresponding constants
LOG_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def get_logger(name=None):
    """
    Get a configured logger instance.

    Args:
        name (str, optional): Logger name. If None, returns the root logger.

    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if handlers haven't been added yet
    if not logger.handlers:
        # Set log level
        level = LOG_LEVEL_MAP.get(LOG_LEVEL, logging.INFO)
        logger.setLevel(level)

        # Create formatters
        formatter = logging.Formatter(LOG_FORMAT)

        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Create file handler
        file_path = os.path.join(LOG_DIR, LOG_FILE)
        file_handler = RotatingFileHandler(
            file_path, maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
