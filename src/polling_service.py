"""Service for polling Linear API for issues tagged with AI."""

import json
import os
import asyncio
from datetime import datetime, timedelta

from .linear_client import LinearClient
from .config import AI_TAG_NAME, DEFAULT_POLL_INTERVAL, PROCESSED_ISSUES_FILE, POLL_LOOKBACK_DAYS
from .issue_processor import process_issue
from .log import get_logger

logger = get_logger()


class LinearPollingService:
    """Service for polling Linear API for issues with AI tag."""

    def __init__(self, poll_interval=DEFAULT_POLL_INTERVAL, state_file_path=PROCESSED_ISSUES_FILE):
        """
        Initialize the polling service.

        Args:
            poll_interval: Interval in seconds between polls
            state_file_path: Path to the file storing processed issue IDs
        """
        self.linear_client = LinearClient()
        self.poll_interval = poll_interval
        self.state_file_path = state_file_path
        self._load_state()
        self.running = False
        self.start_time = datetime.now()  # Track when the program started

    def _load_state(self):
        """Load the state (processed and in-progress issues) from disk."""
        self.processed_issues = set()
        self.in_progress_issues = set()

        if os.path.exists(self.state_file_path):
            try:
                with open(self.state_file_path, "r") as f:
                    data = json.load(f)
                    self.processed_issues = set(data.get("processed_issues", []))
                    self.in_progress_issues = set(data.get("in_progress_issues", []))
                    logger.info(
                        f"Loaded {len(self.processed_issues)} processed issues and {len(self.in_progress_issues)} in-progress issues"
                    )
            except Exception as e:
                logger.error(f"Error loading state file: {str(e)}")

    def _save_state(self):
        """Save the state (processed and in-progress issues) to disk."""
        try:
            with open(self.state_file_path, "w") as f:
                json.dump(
                    {
                        "processed_issues": list(self.processed_issues),
                        "in_progress_issues": list(self.in_progress_issues),
                        "last_updated": datetime.now().isoformat(),
                    },
                    f,
                    indent=2,
                )
        except Exception as e:
            logger.error(f"Error saving state file: {str(e)}")

    async def _process_new_issues(self):
        """Find and process new issues with the AI tag."""
        try:
            # Query for recent AI-tagged issues
            ai_issues = self._get_ai_tagged_issues()

            # Filter out already processed and in-progress issues
            new_issues = [
                issue
                for issue in ai_issues
                if issue["id"] not in self.processed_issues
                and issue["id"] not in self.in_progress_issues
            ]

            if new_issues:
                logger.info(f"Found {len(new_issues)} new AI-tagged issues to process")

                for issue in new_issues:
                    issue_id = issue["id"]

                    # Only process issues in "Todo" status
                    if issue["state"]["name"] != "Todo":
                        logger.info(
                            f"Skipping issue {issue['identifier']}: not in Todo status (current: {issue['state']['name']})"
                        )
                        continue

                    logger.info(f"Processing issue {issue['identifier']}: {issue['title']}")

                    # Mark as in-progress before processing
                    self.in_progress_issues.add(issue_id)
                    self._save_state()

                    # Process the issue
                    try:
                        await process_issue(issue_id)
                        # Mark as processed and remove from in-progress
                        self.processed_issues.add(issue_id)
                        self.in_progress_issues.remove(issue_id)
                        self._save_state()
                        logger.info(f"Successfully processed issue {issue['identifier']}")
                    except Exception as e:
                        logger.error(f"Error processing issue {issue['identifier']}: {str(e)}")
                        # Keep in in-progress list so we can retry later
                        # This allows for transient errors to be retried in future polling cycles
            else:
                logger.info("No new AI-tagged issues found")

            # Check if any in-progress issues have been stuck for too long
            # This could be enhanced with timestamps to detect truly stuck issues
            if self.in_progress_issues:
                logger.info(f"There are {len(self.in_progress_issues)} issues still in progress")

        except Exception as e:
            logger.error(f"Error in polling cycle: {str(e)}")

    def _get_ai_tagged_issues(self):
        """
        Query Linear API for issues with the AI tag.

        Returns:
            List of issue objects
        """
        # If POLL_LOOKBACK_DAYS is 0, use program start time instead of lookback period
        if POLL_LOOKBACK_DAYS == 0:
            lookback_date = self.start_time
            logger.info(f"Using program start time as lookback date: {lookback_date}")
        else:
            # Calculate the date N days ago for the lookback period
            lookback_date = datetime.now() - timedelta(days=POLL_LOOKBACK_DAYS)

        issues = self.linear_client.get_issues_by_label(AI_TAG_NAME, created_after=lookback_date)

        if POLL_LOOKBACK_DAYS == 0:
            logger.info(f"Found {len(issues)} AI-tagged issues updated since program start")
        else:
            logger.info(
                f"Found {len(issues)} AI-tagged issues updated within the last {POLL_LOOKBACK_DAYS} days"
            )
        return issues

    async def start_polling(self):
        """Start the polling loop."""
        logger.info(f"Starting Linear polling service (interval: {self.poll_interval}s)")
        self.running = True

        while self.running:
            logger.info("Polling Linear for AI-tagged issues")
            await self._process_new_issues()

            # Sleep until the next polling interval
            logger.info(f"Next poll in {self.poll_interval} seconds")
            await asyncio.sleep(self.poll_interval)

    def stop_polling(self):
        """Stop the polling loop."""
        logger.info("Stopping Linear polling service")
        self.running = False
