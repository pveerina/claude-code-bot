"""Main entry point for the ClaudeCodeBot application."""

import asyncio
import argparse
import signal
import sys
from .config import validate_config
from .polling_service import LinearPollingService
from .log import get_logger

logger = get_logger()

# Global variable for the polling service instance
polling_service = None


def signal_handler(sig, frame):
    """Handle Ctrl+C signal to gracefully shutdown the application."""
    logger.info("Received shutdown signal")
    if polling_service:
        polling_service.stop_polling()
    sys.exit(0)


async def run_polling_service(interval=60):
    """Run the polling service with the specified interval."""
    global polling_service
    polling_service = LinearPollingService(poll_interval=interval)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await polling_service.start_polling()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        polling_service.stop_polling()
    except Exception as e:
        logger.exception(f"Error in polling service: {str(e)}")
        polling_service.stop_polling()


def main():
    """Main entry point for the application."""
    try:
        parser = argparse.ArgumentParser(description="ClaudeCodeBot")

        parser.add_argument(
            "--interval", type=int, default=60, help="Polling interval in seconds (default: 60)"
        )

        args = parser.parse_args()

        validate_config()

        asyncio.run(run_polling_service(interval=args.interval))

    except Exception as e:
        logger.exception(f"Error starting application: {str(e)}")
        raise


if __name__ == "__main__":
    main()
