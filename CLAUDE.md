# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OmniFocus MCP Server: Exposes OmniFocus task management to Claude Code and other MCP-compatible AI assistants via AppleScript automation on macOS.

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

### Key Components

| File | Purpose |
|------|---------|
| `mcp_server.py` | FastMCP server for Claude Code (stdio transport) |
| `server.py` | FastAPI HTTP server (alternative REST API) |
| `scripts/*.applescript` | Direct OmniFocus automation |
| `utils/applescript.py` | `run_script()` wrapper, `AppleScriptError` |
| `utils/omnifocus.py` | High-level Python API with `Task` dataclass |

### Design Patterns

- **AppleScript as Source of Truth**: All OmniFocus operations happen in AppleScript
- **JSON Communication**: AppleScripts construct JSON strings manually (no JSON library in AppleScript)
- **Dual Interfaces**: MCP server for AI assistants, HTTP server for traditional clients

## Development Commands

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run MCP server (for testing - normally started by Claude Code)
python mcp_server.py

# Run HTTP server
uvicorn server:app --reload

# Test AppleScripts directly
osascript scripts/list_tasks.applescript
osascript scripts/list_tasks.applescript flagged
osascript scripts/add_task.applescript "Task title" "Project name"
```

## MCP Tools

The MCP server exposes these tools to Claude Code:

| Tool | Args | Returns |
|------|------|---------|
| `list_tasks` | `filter?: "due_soon"\|"flagged"\|"inbox"` | `{tasks: [...]}` |
| `summarize_tasks` | `filter?` | `{projects: [{project, active, flagged, due_today, overdue}]}` |
| `add_task` | `title, project?` | `{status: "ok", output: ...}` |
| `get_projects` | none | `{projects: [...]}` |
| `complete_task` | `task_id` | `{status: "ok"}` |

## HTTP Endpoints

All `/mcp/*` endpoints use POST with JSON bodies:

- `GET /health` - Health check
- `POST /mcp/list_tasks` - Optional: `{"filter": "due_soon"|"flagged"|"inbox"}`
- `POST /mcp/summarize_tasks` - Groups tasks by project
- `POST /mcp/add_task` - `{"title": "...", "project": "..."}`
- `POST /mcp/get_projects` - List all projects
- `POST /mcp/complete_task` - `{"task_id": "..."}`

## AppleScript Details

### Date Format
AppleScript formats dates as ISO 8601: `YYYY-MM-DDTHH:MM:SS`

### JSON Construction
Manual string concatenation with helper functions:
- `json_escape()` - Escapes backslash, quotes, newlines
- `iso_date_string()` - Formats dates
- `zero_pad()` - Pads numbers with leading zeros

### Task Fields
- `id`: OmniFocus internal ID
- `name`: Task name
- `project`: Containing project (empty string if none)
- `due`: ISO date or empty string
- `flagged`: boolean
- `completed`: boolean
- `note`: Task notes

## Adding New Tools

1. Create AppleScript in `scripts/` that returns JSON
2. Add tool to `mcp_server.py`:
   ```python
   @mcp.tool()
   def new_tool(arg: str) -> dict:
       """Tool description for the AI."""
       script_path = SCRIPTS_DIR / "new_script.applescript"
       try:
           output = run_script(script_path, arg)
           return json.loads(output)
       except AppleScriptError as exc:
           return {"error": str(exc)}
   ```
3. Optionally add HTTP endpoint in `server.py`

## Dependencies

- `mcp` - Model Context Protocol SDK (includes FastMCP)
- `fastapi` - HTTP server framework
- `uvicorn` - ASGI server
- Python 3.11+
- macOS with OmniFocus installed
