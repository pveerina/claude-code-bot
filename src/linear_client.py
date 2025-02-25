"""Client for interacting with the Linear API."""

import requests
from .config import LINEAR_API_KEY
from .log import get_logger

logger = get_logger()


class LinearClient:
    """Client for interacting with the Linear API."""

    def __init__(self):
        self.api_key = LINEAR_API_KEY
        self.base_url = "https://api.linear.app/graphql"
        self.headers = {"Authorization": f"{self.api_key}", "Content-Type": "application/json"}

    def execute_query(self, query, variables=None):
        """Execute a GraphQL query against the Linear API."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        logger.debug(f"Executing Linear GraphQL query: {query[:100]}...")

        try:
            response = requests.post(self.base_url, json=payload, headers=self.headers)
            response.raise_for_status()

            data = response.json()
            if "errors" in data:
                logger.error(f"Linear API returned errors: {data['errors']}")
                raise Exception(f"Linear API Error: {data['errors']}")

            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to Linear API: {str(e)}")
            raise

    def get_all_issues(self, first=50, include_archived=False):
        """Get all issues.

        Args:
            first (int): Number of issues to return (default: 50)
            include_archived (bool): Whether to include archived issues (default: False)

        Returns:
            list: List of issues
        """
        logger.info(f"Fetching all issues (limit: {first}, include_archived: {include_archived})")

        query = """
        query GetAllIssues($first: Int, $includeArchived: Boolean) {
            issues(first: $first, includeArchived: $includeArchived) {
                nodes {
                    id
                    title
                    identifier
                    description
                    state {
                        id
                        name
                    }
                    team {
                        id
                        name
                    }
                    labels {
                        nodes {
                            id
                            name
                        }
                    }
                }
            }
        }
        """

        variables = {"first": first, "includeArchived": include_archived}

        result = self.execute_query(query, variables)
        return result["data"]["issues"]["nodes"]

    def update_issue_status(self, issue_id, status_id):
        """Update the status of an issue."""
        logger.info(f"Updating issue {issue_id} status to {status_id}")

        query = """
        mutation UpdateIssue($id: String!, $stateId: String!) {
            issueUpdate(id: $id, input: { stateId: $stateId }) {
                issue {
                    id
                    title
                    state {
                        id
                        name
                    }
                }
                lastSyncId
                success
            }
        }
        """

        variables = {"id": issue_id, "stateId": status_id}

        result = self.execute_query(query, variables)
        return result["data"]["issueUpdate"]["success"]

    def create_comment(self, issue_id, body):
        """Create a comment on an issue."""
        logger.info(f"Creating comment on issue {issue_id}")

        query = """
        mutation CreateComment($issueId: String!, $body: String!) {
            commentCreate(input: { issueId: $issueId, body: $body }) {
                success
                comment {
                    id
                    body
                }
            }
        }
        """

        variables = {"issueId": issue_id, "body": body}

        result = self.execute_query(query, variables)
        return result["data"]["commentCreate"]["success"]

    def get_issue_details(self, issue_id):
        """Get details for an issue."""
        logger.info(f"Fetching details for issue {issue_id}")

        query = """
        query GetIssue($id: String!) {
            issue(id: $id) {
                id
                title
                description
                identifier
                url
                createdAt
                updatedAt
                branchName
                team {
                    id
                    name
                    key
                }
                state {
                    id
                    name
                    color
                    type
                }
                assignee {
                    id
                    name
                    email
                }
                creator {
                    id
                    name
                }
                labels {
                    nodes {
                        id
                        name
                        color
                    }
                }
                comments {
                    nodes {
                        id
                        body
                        createdAt
                        user {
                            id
                            name
                        }
                    }
                }
            }
        }
        """

        variables = {"id": issue_id}

        try:
            result = self.execute_query(query, variables)
            return result["data"]["issue"]
        except Exception as e:
            logger.error(f"Error fetching issue details for {issue_id}: {str(e)}")
            raise

    def get_status_id_by_name(self, team_id, status_name):
        """Get the ID of a status by its name within a team."""
        logger.info(f"Fetching status ID for name: {status_name} in team {team_id}")

        query = """
        query GetTeamStates($teamId: String!) {
            team(id: $teamId) {
                states {
                    nodes {
                        id
                        name
                    }
                }
            }
        }
        """

        variables = {"teamId": team_id}

        result = self.execute_query(query, variables)
        states = result["data"]["team"]["states"]["nodes"]

        for state in states:
            if state["name"].lower() == status_name.lower():
                return state["id"]

        logger.warning(f"Could not find status with name '{status_name}' in team {team_id}")
        return None

    def get_issues_by_label(
        self, label_name, first=50, include_archived=False, created_after=None, status_name=None
    ):
        """Get issues that have a specific label with optional additional filters.

        Args:
            label_name (str): The name of the label to filter by
            first (int): Number of issues to return (default: 50)
            include_archived (bool): Whether to include archived issues (default: False)
            created_after (str, optional): ISO format date string to filter issues created after this date
            status_name (str, optional): Filter issues by status name (e.g., "Todo")

        Returns:
            list: List of issues with the specified label and matching filters
        """
        logger.info(
            f"Fetching issues with label: {label_name} (limit: {first}, include_archived: {include_archived}, created_after: {created_after}, status: {status_name})"
        )

        # Build filter object
        filter_obj = {"labels": {"name": {"eq": label_name}}}

        # Add created_after filter if provided
        if created_after:
            filter_obj["createdAt"] = {"gt": created_after.isoformat()}

        # Add status filter if provided
        if status_name:
            filter_obj["state"] = {"name": {"eq": status_name}}

        query = """
        query GetIssuesByLabel($first: Int, $includeArchived: Boolean, $filter: IssueFilter) {
            issues(
                first: $first, 
                includeArchived: $includeArchived,
                filter: $filter
            ) {
                nodes {
                    id
                    title
                    identifier
                    description
                    createdAt
                    state {
                        id
                        name
                    }
                    team {
                        id
                        name
                    }
                    labels {
                        nodes {
                            id
                            name
                        }
                    }
                }
            }
        }
        """

        variables = {"first": first, "includeArchived": include_archived, "filter": filter_obj}

        result = self.execute_query(query, variables)
        return result["data"]["issues"]["nodes"]
