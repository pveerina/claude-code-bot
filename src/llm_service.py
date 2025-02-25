"""Service for interacting with Anthropic's Claude LLM API."""

import json
import requests
from .config import LLM_API_KEY, LLM_API_URL, LLM_MAX_TOKENS
from .log import get_logger

logger = get_logger()

CLAUDE_HAIKU_MODEL = "claude-3-5-haiku-20241022"
CLAUDE_SONNET_MODEL = "claude-3-5-sonnet-20241022"


class LLMService:
    """Service for interacting with Anthropic's Claude API."""

    def __init__(self):
        self.api_key = LLM_API_KEY
        self.api_url = LLM_API_URL
        self.max_tokens = LLM_MAX_TOKENS

    def _call_llm(self, messages, model=CLAUDE_HAIKU_MODEL, temperature=0.2, response_format=None):
        """
        Call the Claude API with the provided messages.

        Args:
            messages: List of message objects (role, content)
            temperature: Temperature parameter for generation
            response_format: Optional format specification for the response

        Returns:
            The model's response content
        """
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        system_message = ""
        user_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            elif msg["role"] == "user":
                user_messages.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                user_messages.append({"role": "assistant", "content": msg["content"]})

        # Anthropic API expects alternating user/assistant messages, starting with user
        # For simplicity, we'll just take the last user message if multiple exist
        _ = next((msg["content"] for msg in reversed(user_messages) if msg["role"] == "user"), "")

        payload = {
            "model": model,
            "max_tokens": self.max_tokens,
            "temperature": temperature,
            "system": system_message,
            "messages": user_messages,
        }

        # Handle JSON mode for Claude
        if response_format and response_format.get("type") == "json_object":
            # Add instruction to response in JSON format
            if system_message:
                payload["system"] = system_message + "\nYou must respond with valid JSON."
            else:
                payload["system"] = "You must respond with valid JSON."

        try:
            logger.debug(f"Calling Claude API with request payload of {len(str(payload))} chars")
            response = requests.post(
                self.api_url, headers=headers, json=payload, timeout=60  # 60 second timeout
            )
            response.raise_for_status()

            result = response.json()
            content = result.get("content", [{"text": ""}])[0].get("text", "")

            logger.debug(f"Claude response received ({len(content)} chars)")
            return content

        except requests.exceptions.RequestException as e:
            logger.error(f"Claude API request failed: {str(e)}")
            if hasattr(e, "response") and e.response:
                logger.error(f"Response: {e.response.text}")
            raise

    def evaluate_result(self, description, result, modified_files):
        """
        Evaluate if the code generation was successful.

        Args:
            description: The original issue description
            result: The output from the code generation

        Returns:
            A tuple of (success, reasoning)
        """
        logger.info("Evaluating code generation result with Claude")

        prompt = [
            {
                "role": "system",
                "content": "You are a process supervisor evaluating the result from a coding agent. The agent will provide a summary of the changes it made to the codebase and the files it modified. You must determine if the provided information should be sufficient to proceed to code review.",
            },
            {
                "role": "user",
                "content": f"""
            Task Description:
            {description}
            
            Result Summary:
            {result}

            Modified Files (from git):
            {modified_files}
            
            Evaluate if the process should proceed to code review:
            If the result summary is clear and the files that were modified are relevant to the task description, you should respond with yes.
            If the result summary contains transient errors such as (api re-connecting) or other issues you can ingore it as long as the summary is sufficient to proceed.
            If the result summary contains a question or a request for more information, you should respond with no and provide a clear explanation for why.
            
            Please provide:
            1. A yes/no decision on whether the result should proceed to code review
            2. Your reasoning for this decision
            
            Format your response as a JSON object with "success" (boolean) and "reasoning" (string) fields.
            """,
            },
        ]

        try:
            content = self._call_llm(
                prompt,
                model=CLAUDE_SONNET_MODEL,
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            # Parse the JSON response
            evaluation = json.loads(content)

            logger.info(f"Claude evaluation: success={evaluation['success']}")

            return evaluation["success"], evaluation["reasoning"]

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing Claude response: {str(e)}")
            return False, f"Error evaluating result: {str(e)}"

    def generate_pr_content(self, description, result, modified_files):
        """
        Generate a commit message and PR description.

        Args:
            description: The original issue description
            result: The output from the code generation

        Returns:
            A tuple of (commit_message, pr_description)
        """
        logger.info("Generating PR content with Claude")

        prompt = [
            {
                "role": "system",
                "content": "You are an expert developer who writes clear, concise commit messages and pull request descriptions. Format your response as JSON.",
            },
            {
                "role": "user",
                "content": f"""
            Task Description:
            {description}
            
            Claude Code Output:
            {result}

            Modified Files (from git):
            {modified_files}
            
            Please generate:
            1. A concise commit message (one line)
            2. A pull request description. The PR description should have 3 parts, summary, details (this should include the claude code output as well as any other reasoning/details), and note that the code was generated by ClaudeCodeBot an AI code generation tool, and that results should be reviewed carefully.
            
            Format your response as a JSON object with "commit_message" and "pr_description" fields.
            """,
            },
        ]

        try:
            content = self._call_llm(
                prompt,
                model=CLAUDE_SONNET_MODEL,
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            # Parse the JSON response
            pr_content = json.loads(content)

            logger.info(f"Generated commit message: {pr_content['commit_message']}")

            return pr_content["commit_message"], pr_content["pr_description"]

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing Claude response: {str(e)}")
            return (
                "AI-generated changes",
                "This PR was automatically generated by the AI automation system.",
            )

    def format_issue_description(self, description):
        """
        Format the issue description for better parsing by the code generation tool.

        Args:
            description: The original issue description

        Returns:
            Formatted description
        """
        logger.info("Formatting issue description with Claude")

        prompt = [
            {
                "role": "system",
                "content": "You are an expert at reformatting requirements into clear, structured specifications for code generation tools.",
            },
            {
                "role": "user",
                "content": f"""
            Please format the following issue description to be clear, structured, and easy to understand for a code generation tool:

            {description}
            
            Focus on:
            - Structuring information logically
            - Highlighting key technical details
            - For complex problems, explicitly ask Claude to think more deeply. 

            Return only the formatted description, without any additional comments. Do not change the task, just make it more clear and structured.
            Do not make up any additional details, just use the ones provided. If the provided description is simple, do not make it more complex.
            """,
            },
        ]

        formatted_description = self._call_llm(prompt, model=CLAUDE_HAIKU_MODEL, temperature=0.2)

        logger.info("Issue description formatted successfully")

        return formatted_description
