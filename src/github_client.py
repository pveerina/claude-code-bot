"""Client for interacting with the GitHub API."""

import requests
from .config import GITHUB_TOKEN, GITHUB_REPO
from .log import get_logger

logger = get_logger()


class GitHubClient:
    """Client for interacting with the GitHub API."""

    def __init__(self):
        self.token = GITHUB_TOKEN
        # remove prefix if present
        if GITHUB_REPO.startswith("https://github.com/"):
            stripped_repo = GITHUB_REPO[len("https://github.com/") :]
        else:
            stripped_repo = GITHUB_REPO
        owner, repo = stripped_repo.split("/")
        self.owner = owner
        self.repo = repo
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def create_pull_request(self, branch, title, description, base_branch="main"):
        """Create a pull request."""
        logger.info(f"Creating pull request for branch {branch}")

        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/pulls"
        payload = {"title": title, "body": description, "head": branch, "base": base_branch}

        response = requests.post(url, json=payload, headers=self.headers)

        if response.status_code == 422:
            # This might happen if the PR already exists or there are no changes
            logger.warning(
                f"Could not create PR: {response.json().get('message', 'Unknown error')}"
            )
            return None

        response.raise_for_status()

        data = response.json()
        logger.info(f"Created pull request: {data['html_url']}")

        return data

    def add_labels_to_pr(self, pr_number, labels):
        """Add labels to a pull request."""
        logger.info(f"Adding labels {labels} to PR #{pr_number}")

        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/issues/{pr_number}/labels"
        payload = {"labels": labels}

        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()

        return response.json()

    def get_repo_details(self):
        """Get details about the repository."""
        logger.info(f"Fetching details for repo {self.owner}/{self.repo}")

        url = f"{self.base_url}/repos/{self.owner}/{self.repo}"

        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        return response.json()
