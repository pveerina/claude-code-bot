"""Handles Git operations like cloning, checking out branches, and committing."""

import os
import subprocess
from .config import WORKING_DIRECTORY, GITHUB_TOKEN, MAIN_BRANCH, GITHUB_REPO
from .log import get_logger

logger = get_logger()


class GitOperations:
    """Handles Git operations like cloning, checking out branches, and committing."""

    def __init__(self):
        self.repo = GITHUB_REPO
        self.token = GITHUB_TOKEN
        self.main_branch = MAIN_BRANCH
        self.repo_path = WORKING_DIRECTORY + "/code"

        # Ensure the repository directory exists
        if not os.path.exists(self.repo_path):
            os.makedirs(self.repo_path)

    def _run_command(self, command, cwd=None, check=True):
        """Run a shell command and return its output."""
        if cwd is None:
            cwd = self.repo_path

        logger.info(f"Running command: {' '.join(command)}")

        try:
            result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=check)
            return result.stdout.strip(), result.stderr.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e.stderr}")
            if check:
                raise
            return e.stdout.strip() if e.stdout else "", e.stderr.strip() if e.stderr else ""

    def ensure_repo_cloned(self):
        """Ensure the repository is cloned locally."""
        if not os.path.exists(os.path.join(self.repo_path, ".git")):
            logger.info(f"Cloning repository {self.repo}")

            # Use HTTPS URL with token for authentication
            repo_url = f"https://{self.token}@{self.repo.replace('https://', '')}"

            self._run_command(["git", "clone", repo_url, "."], cwd=self.repo_path)
            # Configure Git user for this repo
            self._run_command(["git", "config", "user.name", "ClaudeCodeBot"])
            self._run_command(["git", "config", "user.email", "claude-code-bot@example.com"])

    def checkout_main_and_pull(self):
        """Checkout the main branch and pull the latest changes."""
        logger.info(f"Checking out {self.main_branch} branch and pulling latest changes")
        # Force discard any changes if needed
        try:
            # Check if there are any changes to discard
            status_out, _ = self._run_command(["git", "status", "--porcelain"], check=False)

            if status_out:
                logger.info("Discarding local changes before checkout")
                # Reset any staged changes
                self._run_command(["git", "reset", "--hard", "HEAD"], check=False)
                # Clean untracked files and directories
                self._run_command(["git", "clean", "-fd"], check=False)
        except Exception as e:
            logger.warning(f"Error while discarding changes: {str(e)}")
        self._run_command(["git", "checkout", self.main_branch])
        self._run_command(["git", "pull", "origin", self.main_branch])

    def create_and_checkout_branch(self, branch_name):
        """Create and checkout a new branch based on the main branch."""
        logger.info(f"Creating and checking out branch: {branch_name}")

        # First checkout main to ensure the new branch is based on it
        self.checkout_main_and_pull()

        # Check if branch already exists
        stdout, _ = self._run_command(["git", "branch", "--list", branch_name], check=False)

        if branch_name in stdout:
            logger.info(f"Branch {branch_name} already exists, checking it out")
            self._run_command(["git", "checkout", branch_name])
        else:
            # Create and checkout the new branch
            self._run_command(["git", "checkout", "-b", branch_name])

    def commit_changes(self, commit_message):
        """Commit all changes in the working directory."""
        logger.info("Committing changes")

        # Check if there are any changes to commit
        status_out, _ = self._run_command(["git", "status", "--porcelain"])

        if not status_out:
            logger.info("No changes to commit")
            return False

        self._run_command(["git", "add", "."])
        self._run_command(["git", "commit", "-m", commit_message])
        return True

    def push_branch(self, branch_name):
        """Push the branch to the remote repository."""
        logger.info(f"Pushing branch {branch_name} to remote")

        self._run_command(["git", "push", "origin", branch_name])

    def get_modified_files(self):
        """Get a list of modified files from git."""
        stdout, _ = self._run_command(["git", "status", "--porcelain"])
        modified_files = []

        for line in stdout.splitlines():
            stripped_line = line.strip()
            if stripped_line and stripped_line != "":
                modified_files.append(stripped_line)

        return modified_files
