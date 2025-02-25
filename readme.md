# ClaudeCodeBot

ClaudeCodeBot allows you to tag linear issues with "AI" and have [claude code](https://github.com/anthropics/claude-code) automatically generate a pull request on github.

**WARNING: This is an experimental project - use at your own risk!** Running a coding agents, even with a docker environment to somewhat isolate your host system, does not completely mitigate the risks.

## How it works
ClaudeCodeBot listens (or polls) for Linear events on issues tagged with "AI" (or any other tag you want to use).
When a new issue is detected, ClaudeCodeBot checks out the suggested branch name and runs [claude code](https://github.com/anthropics/claude-code) in a docker container using a summarized version of the issue title + description as the prompt. It then reports back its progress on the original ticket and opens a pull request if successful.


## Getting Started

### Prerequisites
- Python 3.9+
- Docker
- Git
- Linear API access
- GitHub API access
- Anthropic API access

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/pveerina/claude-code-bot.git
   cd claude-code-bot
   ```

2. Set up a virtual environment using uv: 
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -e 
   ```

4. Install [claude code](https://github.com/anthropics/claude-code) and initialize it to produce the ~/.claude.json config file

4. Build the [claude code](https://github.com/anthropics/claude-code) docker image:
   ```bash
   git clone https://github.com/anthropics/claude-code
   cd claude-code/.devcontainer
   docker build -t claude-code .
   ```

5. Create a configuration file and fill in your API keys and configuration:
   ```bash
   cp .env.example .env
   ```

#### Config details
- `LINEAR_API_KEY`: Your Linear API key
- `AI_TAG_NAME`: Name of the tag that triggers automation (default: "AI")
- `GITHUB_TOKEN`: GitHub personal access token
- `GITHUB_REPO`: URL of the repository
- `MAIN_BRANCH`: Name of the main branch (default: "main")
- `DOCKER_IMAGE`: Docker image to use for code generation. (default: "claude-code")
- `WORKING_DIRECTORY`: Path to the directory where the repository will be cloned (default: "./repo")
- `LLM_API_KEY`: API key for Anthropic
- `LLM_MAX_TOKENS`: Maximum tokens in Claude responses (default: 1000)
- `CLAUDE_CODE_CONFIG`: Path to the Claude Code configuration file. You will need to create this file by running [claude code](https://github.com/anthropics/claude-code) locally and doing the oauth dance, it then gets saved to `~/.claude.json`.)


## Usage

1. Start the bot
```bash
python -m src.main
```

2. Create an issue in Linear and add the "AI" tag. Include a detailed description of the task for best results.

Notes:
- Currently the bot only supports polling for issues. Webhooks are not supported yet.
- The `--interval` parameter (in seconds) is optional and defaults to 60 seconds.
- The bot maintains a local state file (`data/issues.json` by default) to track which issues have been processed, preventing duplicated work across restarts.

