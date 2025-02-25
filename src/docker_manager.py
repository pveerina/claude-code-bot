"""Manages Docker containers for code generation."""

import os
import subprocess
import json
from time import time
from .config import DOCKER_IMAGE, WORKING_DIRECTORY, CLAUDE_CODE_CONFIG
from .log import get_logger

logger = get_logger()


class DockerManager:
    """Manages Docker containers for code generation."""

    def __init__(self):
        self.docker_image = DOCKER_IMAGE
        self.working_directory = WORKING_DIRECTORY

    def _run_command(self, command):
        """Run a shell command and return its output."""
        logger.info(f"Running command: {' '.join(command)}")

        result = subprocess.run(command, capture_output=True, text=True, check=True)

        return result.stdout.strip(), result.stderr.strip()

    def check_docker_installed(self):
        """Check if Docker is installed and running."""
        try:
            self._run_command(["docker", "--version"])
            self._run_command(["docker", "ps"])
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Docker check failed: {str(e)}")
            return False

    def run_code_generation(self, issue_id, original_description, formatted_description):
        """Run code generation in a Docker container."""
        logger.info("Running code generation in Docker container")

        # Check Docker is installed and running
        if not self.check_docker_installed():
            raise RuntimeError("Docker is not installed or not running")

        # Check if image exists locally
        try:
            self._run_command(["docker", "image", "inspect", self.docker_image])
        except subprocess.CalledProcessError:
            raise RuntimeError(
                f"Docker image {self.docker_image} not found locally. Please pull the image first."
            )

        # Create directory for this issue on this run if it doesn't exist
        timestamp = str(int(time()))
        issue_ts = f"{issue_id}_{timestamp}"
        issue_dir = os.path.join(self.working_directory, issue_ts)
        os.makedirs(issue_dir, exist_ok=True)
        input_file_path = os.path.join(issue_dir, "input.json")
        input_data = {
            "original_description": original_description,
            "formatted_description": formatted_description,
            "metadata": {
                "timestamp": str(int(time())),
                "issue_id": issue_id,
            },
        }

        with open(input_file_path, "w") as f:
            json.dump(input_data, f)

        prompt_file_path = os.path.join(issue_dir, "prompt.txt")
        with open(prompt_file_path, "w") as f:
            f.write(formatted_description)

        try:
            # Get absolute path to the repo
            abs_working_directory = os.path.abspath(self.working_directory)
            prompt_path = f"/mnt/{issue_ts}/prompt.txt"

            # Build the Docker command
            command = [
                "docker",
                "run",
                "--rm",  # Remove container after execution
                "--cap-add=NET_RAW",
                "--cap-add=NET_ADMIN",
                "-v",
                f"{abs_working_directory}:/mnt",  # Mount the repository
                "-v",
                f"{CLAUDE_CODE_CONFIG}:/home/node/.claude.json",  # Mount the claude config
                "-w",
                "/mnt/code",  # Set working directory to code dir
                self.docker_image,
                "/bin/sh",
                "-c",
                f'sudo /usr/local/bin/init-firewall.sh > /dev/null 2>&1 && claude --dangerously-skip-permissions -p "$(cat {prompt_path})"',  # Redirect firewall output to /dev/null, only get claude output
            ]

            # Run the Docker container
            stdout, stderr = self._run_command(command)

            stdout_file_path = os.path.join(issue_dir, "stdout.txt")
            stderr_file_path = os.path.join(issue_dir, "stderr.txt")

            with open(stdout_file_path, "w") as f:
                f.write(stdout)

            with open(stderr_file_path, "w") as f:
                f.write(stderr)

            if stderr:
                logger.warning(f"Docker container produced stderr: {stderr}")

            logger.info(f"Docker container completed with output ({len(stdout)} chars)")
            logger.debug(f"Docker output: {stdout[:500]}...")
            return stdout

        except subprocess.CalledProcessError as e:
            logger.error(f"Docker container execution failed: {e.stderr}")
            raise
