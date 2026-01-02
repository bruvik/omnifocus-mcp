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

## Usage with Claude Desktop

Edit Claude Desktop's config file at `~/Library/Application Support/Claude/claude_desktop_config.json`:

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

Replace `/path/to/omnifocus-mcp` with the actual path to this repository.

Restart Claude Desktop after editing the config.

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

### Verify Installation (Claude Code)

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
| `list_tasks` | List tasks with optional filter (due_soon, flagged, inbox, all, completed, deferred) |
| `summarize_tasks` | Get task counts grouped by project |
| `add_task` | Create a new task with full options (project, due, defer, flagged, note, rrule) |
| `get_projects` | List all OmniFocus projects |
| `complete_task` | Mark a task as completed by ID |
| `rename_task` | Rename a task |
| `move_task` | Move a task to a different project or inbox |
| `delete_task` | Permanently delete a task by ID |
| `flag_task` | Flag or unflag a task |
| `defer_task` | Set or clear a task's defer date |
| `set_due_date` | Set or clear a task's due date |
| `set_repetition` | Set or clear a task's repetition rule (RRULE format) |
| `drop_project` | Drop (abandon) a project |
| `pause_project` | Put a project on hold |
| `resume_project` | Reactivate a paused project |
| `list_tags` | List all tags with hierarchy info |
| `get_task_tags` | Get tags assigned to a task |
| `add_task_tags` | Add tags to a task (keeps existing) |
| `remove_task_tags` | Remove tags from a task |
| `set_task_tags` | Replace all tags on a task |
| `get_task_note` | Get a task's note/description |
| `set_task_note` | Set a task's note (replaces existing) |
| `append_task_note` | Append text to a task's note |
| `clear_task_note` | Clear/remove a task's note |

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
# List available tasks (default)
osascript scripts/list_tasks_omni.applescript

# List with filter
osascript scripts/list_tasks_omni.applescript flagged
osascript scripts/list_tasks_omni.applescript due_soon
osascript scripts/list_tasks_omni.applescript all

# Add task (JSON format)
osascript scripts/add_task_omni.applescript '{"title": "Task name", "project": "Project name"}'
osascript scripts/add_task_omni.applescript '{"title": "Weekly review", "rrule": "FREQ=WEEKLY", "flagged": true}'

# Set repetition
osascript scripts/set_repetition.applescript "task-id" "FREQ=DAILY" "due"
osascript scripts/set_repetition.applescript "task-id" "none"  # Clear repetition

# Update task
osascript scripts/update_task.applescript "task-id" flag
osascript scripts/update_task.applescript "task-id" defer "2025-01-15T09:00:00"

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

GPL v3 - See [LICENSE](LICENSE) file for details.

## Todo

- [x] Handle recurring events (RRULE format with set_repetition and add_task rrule param)
- [x] Rename tasks (rename_task tool)
- [x] Handle notes (add_task supports note parameter)
- [x] Create task should be able to create a task in a specific project (already works)
- [x] Move task around in the Projects hierarchy (move_task tool)
- [x] Manipulate tags on tasks (list_tags, get/add/remove/set_task_tags)
- [x] Logic to read, write and manipulate notes on existing tasks (get/set/append/clear_task_note)
- [ ] Handle locations
