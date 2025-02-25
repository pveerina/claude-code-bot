"""Configuration management for the application."""

import os
from log import get_logger
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Linear API configuration
LINEAR_API_KEY = os.environ.get("LINEAR_API_KEY")
LINEAR_WEBHOOK_SECRET = os.environ.get("LINEAR_WEBHOOK_SECRET")

# GitHub configuration
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
MAIN_BRANCH = os.environ.get("MAIN_BRANCH", "main")

# Docker configuration
DOCKER_IMAGE = os.environ.get("DOCKER_IMAGE")
WORKING_DIRECTORY = os.environ.get("WORKING_DIRECTORY", "./repo")
CLAUDE_CODE_CONFIG = os.environ.get("CLAUDE_CODE_CONFIG")
# LLM configuration
LLM_API_KEY = os.environ.get("LLM_API_KEY")
LLM_API_URL = os.environ.get("LLM_API_URL", "https://api.anthropic.com/v1/messages")
LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "1000"))


# Server configuration
SERVER_HOST = os.environ.get("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.environ.get("SERVER_PORT", "8000"))

# AI tag configuration
AI_TAG_NAME = os.environ.get("AI_TAG_NAME", "AI")

# Polling configuration
DEFAULT_POLL_INTERVAL = int(os.environ.get("DEFAULT_POLL_INTERVAL", "60"))
PROCESSED_ISSUES_FILE = os.environ.get("PROCESSED_ISSUES_FILE", "logs/issues.json")
POLL_LOOKBACK_DAYS = int(os.environ.get("POLL_LOOKBACK_DAYS", "7"))


def validate_config():
    """Validate that all required environment variables are set."""
    logger = get_logger()

    required_vars = [
        "LINEAR_API_KEY",
        "LINEAR_WEBHOOK_SECRET",
        "GITHUB_TOKEN",
        "GITHUB_REPO",
        "DOCKER_IMAGE",
        "LLM_API_KEY",
        "CLAUDE_CODE_CONFIG",
    ]

    missing_vars = [var for var in required_vars if not globals()[var]]

    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.error(error_msg)
        raise EnvironmentError(error_msg)

    logger.info("Configuration validated successfully")
