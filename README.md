# OmniFocus MCP Server

MCP (Model Context Protocol) server that exposes OmniFocus task management to Claude Code and other MCP-compatible AI assistants via AppleScript automation.

## Prerequisites

- macOS with OmniFocus installed
- Python 3.11+
- OmniFocus must be running for tasks to work

## Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage with Claude Code

### Option 1: Add via CLI (Recommended)

```bash
# Use the venv's Python to ensure dependencies are available
claude mcp add omnifocus -- /path/to/omnifocus-mcp/.venv/bin/python /path/to/omnifocus-mcp/mcp_server.py
```

Replace `/path/to/omnifocus-mcp` with the actual path to this repository.

### Option 2: Add to project config

Create or edit `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "omnifocus": {
      "command": "/path/to/omnifocus-mcp/.venv/bin/python",
      "args": ["/path/to/omnifocus-mcp/mcp_server.py"]
    }
  }
}
```

### Option 3: Add to user config

Edit `~/.claude.json`:

```json
{
  "mcpServers": {
    "omnifocus": {
      "command": "/path/to/omnifocus-mcp/.venv/bin/python",
      "args": ["/path/to/omnifocus-mcp/mcp_server.py"]
    }
  }
}
```

### Verify Installation

```bash
# List configured MCP servers
claude mcp list

# Test the OmniFocus server
claude mcp get omnifocus
```

## Available MCP Tools

Once connected, Claude Code can use these tools:

| Tool | Description |
|------|-------------|
| `list_tasks` | List tasks with optional filter (due_soon, flagged, inbox) |
| `summarize_tasks` | Get task counts grouped by project |
| `add_task` | Create a new task (optionally in a specific project) |
| `get_projects` | List all OmniFocus projects |
| `complete_task` | Mark a task as completed by ID |

### Example Prompts for Claude Code

- "Show me my flagged tasks in OmniFocus"
- "Add a task 'Review PR #123' to my Work project"
- "What's overdue in OmniFocus?"
- "Complete the task with ID xyz123"
- "Give me a summary of my tasks by project"

## HTTP Server (Alternative)

If you need a REST API instead of MCP, use the FastAPI server:

```bash
# Development mode with auto-reload
uvicorn server:app --reload

# Production mode
uvicorn server:app --host 0.0.0.0 --port 8000
```

### HTTP Endpoints

- `GET /health` - Health check
- `POST /mcp/list_tasks` - Body: `{"filter": "due_soon"|"flagged"|"inbox"}`
- `POST /mcp/summarize_tasks` - Get task summary by project
- `POST /mcp/add_task` - Body: `{"title": "...", "project": "..."}`
- `POST /mcp/get_projects` - List all projects
- `POST /mcp/complete_task` - Body: `{"task_id": "..."}`

## Testing AppleScripts Directly

```bash
# List all tasks
osascript scripts/list_tasks.applescript

# List with filter
osascript scripts/list_tasks.applescript flagged

# Add task
osascript scripts/add_task.applescript "Task title" "Project name"

# Get projects
osascript scripts/get_projects.applescript

# Complete task
osascript scripts/complete_task.applescript "task-id-here"
```

## Architecture

```
┌──────────────┐     stdio/JSON-RPC     ┌─────────────────┐
│ Claude Code  │ ◄────────────────────► │  mcp_server.py  │
└──────────────┘                        └────────┬────────┘
                                                 │ osascript
                                                 ▼
                                        ┌─────────────────┐
                                        │   OmniFocus     │
                                        │   (AppleScript) │
                                        └─────────────────┘
```

- **MCP Server** (`mcp_server.py`): FastMCP-based server using stdio transport
- **HTTP Server** (`server.py`): Alternative REST API via FastAPI
- **AppleScripts** (`scripts/`): Direct OmniFocus automation
- **Utilities** (`utils/`): Python wrappers for AppleScript execution

## License

MIT
