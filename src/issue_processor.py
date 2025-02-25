"""Module for processing Linear issues tagged with AI."""

import asyncio
from .linear_client import LinearClient
from .github_client import GitHubClient
from .git_operations import GitOperations
from .docker_manager import DockerManager
from .llm_service import LLMService
from .config import MAIN_BRANCH
from .log import get_logger

logger = get_logger()

# Initialize clients and services
linear_client = LinearClient()
github_client = GitHubClient()
git_ops = GitOperations()
docker_manager = DockerManager()
llm_service = LLMService()

# Create a semaphore to prevent multiple instances from running concurrently on the same repository
semaphore = asyncio.Semaphore(1)


async def process_issue(issue_id):
    """Process an issue tagged with AI."""
    logger.info(f"Queued AI issue: {issue_id}")

    async with semaphore:
        logger.info(f"Processing AI issue: {issue_id}")
        try:
            # Get issue details
            issue = linear_client.get_issue_details(issue_id)
            logger.info(f"Retrieved issue: {issue['identifier']} - {issue['title']}")

            comment_body = (
                "👋 ClaudeCodeBot here! I'm taking a look at this issue and will update shortly."
            )
            linear_client.create_comment(issue_id, comment_body)
            logger.info("Added initial comment to the issue")

            # Update issue status to in-progress
            team_id = issue["team"]["id"]
            in_progress_status_id = linear_client.get_status_id_by_name(team_id, "In Progress")

            if in_progress_status_id:
                linear_client.update_issue_status(issue_id, in_progress_status_id)
                logger.info("Updated issue status to In Progress")
            else:
                logger.warning("Could not find 'In Progress' status")

            # Format the issue description
            original_description = issue["description"] or ""

            if original_description == "":
                raise Exception("Issue description is empty")

            formatted_description = llm_service.format_issue_description(original_description)
            logger.info("Formatted issue description")

            # Ensure repository is cloned (run in thread to avoid blocking)
            git_ops.ensure_repo_cloned()

            # Create a branch name based on the issue identifier
            branch_name = issue["branchName"] or f"ai/{issue['identifier'].lower()}"

            # Checkout a fresh branch (run in thread to avoid blocking)
            git_ops.create_and_checkout_branch(branch_name)
            logger.info(f"Created and checked out branch: {branch_name}")

            # Run code generation in Docker (run in thread to avoid blocking)
            result = docker_manager.run_code_generation(
                issue_id, original_description, formatted_description
            )
            logger.info("Completed code generation")

            # Check if there are any changes
            modified_files = git_ops.get_modified_files()
            if len(modified_files) == 0:
                logger.warning("No changes were made by the code generation")
                comment_body = (
                    "⚠️ The code generation process did not make any changes to the codebase."
                )
                linear_client.create_comment(issue_id, comment_body)

                # Update issue status back to todo
                todo_status_id = linear_client.get_status_id_by_name(team_id, "Todo")
                if todo_status_id:
                    linear_client.update_issue_status(issue_id, todo_status_id)
                    logger.info("Updated issue status to Todo")

                return

            # Evaluate the result (run in thread to avoid blocking)
            success, reasoning = llm_service.evaluate_result(
                formatted_description, result, modified_files
            )

            if success:
                # Generate commit message and PR description (run in thread to avoid blocking)
                commit_message, pr_description = llm_service.generate_pr_content(
                    formatted_description, result, modified_files
                )

                # Commit changes (run in thread to avoid blocking)
                commit_success = git_ops.commit_changes(commit_message)

                if commit_success:
                    logger.info(f"Committed changes with message: {commit_message}")

                    # Push branch (run in thread to avoid blocking)
                    git_ops.push_branch(branch_name)
                    logger.info(f"Pushed branch: {branch_name}")

                    # Create pull request (run in thread to avoid blocking)
                    pr_title = f"{issue['identifier']}: {issue['title']}"
                    pr_data = github_client.create_pull_request(
                        branch_name, pr_title, pr_description, MAIN_BRANCH
                    )

                    if pr_data:
                        # Add comment to Linear issue with PR link
                        comment_body = f"✅ ClaudeCodeBot created pull request: {pr_data['html_url']}\n\n{pr_description}\n\n**Evaluation:**\n{reasoning}"
                        linear_client.create_comment(issue_id, comment_body)
                        logger.info("Added PR link to Linear issue")

                        # Update issue status (optional - could move to "Ready for Review")
                        ready_status_id = linear_client.get_status_id_by_name(
                            team_id, "Ready for Review"
                        )
                        if ready_status_id:
                            linear_client.update_issue_status(issue_id, ready_status_id)
                            logger.info("Updated issue status to Ready for Review")
                    else:
                        comment_body = f"⚠️ ClaudeCodeBot committed and pushed changes to branch `{branch_name}`, but PR creation failed. You may need to create the PR manually."
                        linear_client.create_comment(issue_id, comment_body)
                        logger.warning("PR creation failed, added comment to issue")
                else:
                    logger.warning("No changes to commit")
                    comment_body = "⚠️ ClaudeCodeBot did not make any changes to the codebase."
                    linear_client.create_comment(issue_id, comment_body)
            else:
                # Add comment to Linear issue with the failure details
                comment_body = f"❌ ClaudeCodeBot was unsuccessful:\n\n**Reasoning:**\n{reasoning}\n\n**Result:**\n```\n{result}\n```"
                linear_client.create_comment(issue_id, comment_body)
                logger.info("Added failure details to Linear issue")

                # Update issue status back to todo
                todo_status_id = linear_client.get_status_id_by_name(team_id, "Todo")
                if todo_status_id:
                    linear_client.update_issue_status(issue_id, todo_status_id)
                    logger.info("Updated issue status to Todo")

        except Exception as e:
            logger.exception(f"Error processing issue {issue_id}: {str(e)}")

            # Add error comment to issue
            try:
                error_comment = f"❌ ClaudeCodeBot encountered an error while processing this issue:\n\n```\n{str(e)}\n```"
                linear_client.create_comment(issue_id, error_comment)
            except Exception as comment_error:
                logger.exception(f"Error adding comment to issue: {str(comment_error)}")
