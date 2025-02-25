# ClaudeCodeBot

ClaudeCodeBot allows you to tag linear issues with "AI" and have claude-code automatically generate a pull request on github.

This is an experimental project - use at your own risk!

## How it works

This is a python application that:

1. Listens (or polls) for Linear events on issues tagged with "AI" (or any other tag you want to use).
2. Automatically processes each issue by:
   - Checking out a fresh branch based on the issue
   - Running a claude-code docker container to generate code based on the issue description
   - Creating a pull request if successful, or adding feedback if not

## Getting Started

### Prerequisites
- Python 3.9+
- Docker
- Git
- Linear API access
- GitHub API access
- Anthropic API access

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/pveerina/claude-code-bot.git
   cd claude-code-bot
   ```

2. Set up a virtual environment using uv: 
   ```bash
   uv venv
   source .venv/bin/activate  
   ```

3. Install dependencies:
   ```bash
   uv pip install -e .
   ```

4. Create a configuration file:
   ```bash
   cp .env.example .env
   ```

5. Build the claude-code docker image:
   ```bash
   git clone https://github.com/anthropics/claude-code
   cd claude-code/.devcontainer
   docker build -t claude-code .
   ```

6. Edit the `.env` file with your API keys and configuration

### Configuration

The application is configured using environment variables in the `.env` file:

#### Linear Configuration
- `LINEAR_API_KEY`: Your Linear API key
- `AI_TAG_NAME`: Name of the tag that triggers automation (default: "AI")

#### Git Configuration
- `GITHUB_TOKEN`: GitHub personal access token
- `GITHUB_REPO`: URL of the repository
- `MAIN_BRANCH`: Name of the main branch (default: "main")

#### Docker Configuration
- `DOCKER_IMAGE`: Docker image to use for code generation. (default: "claude-code")
- `WORKING_DIRECTORY`: Path to the directory where the repository will be cloned (default: "./repo")

#### LLM Configuration
- `LLM_API_KEY`: API key for Anthropic
- `LLM_MAX_TOKENS`: Maximum tokens in Claude responses (default: 1000)

#### Claude Code Configuration
- `CLAUDE_CODE_CONFIG`: Path to the Claude Code configuration file. You will need to create this file by running claude-code locally and doing the oauth dance, it then gets saved to `~/.claude.json`.)


## Usage

The application currently only supports polling for issues. Webhooks are not supported yet.

### Polling Mode 

Use this mode for polling for issues without exposing endpoints:

1. Start the application in polling mode:
   ```bash
   python -m src.main --poll --interval 60
   ```
   The `--interval` parameter (in seconds) is optional and defaults to 60 seconds.

In polling mode, the application maintains a local state file (`data/issues.json` by default) to track which issues have been processed, preventing duplicated work across restarts.

### Creating AI Tasks

1. Create an issue in Linear and add the "AI" tag
2. The application will process the issue and either:
   - Create a pull request with the generated code
   - Add a comment explaining why the generation was unsuccessful

