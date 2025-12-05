# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OmniFocus MCP Server: FastAPI-based HTTP server that exposes OmniFocus task management functionality to Model Context Protocol (MCP) hosts via AppleScript automation on macOS.

## Architecture

### Three-Layer Design

1. **FastAPI Server** (`server.py`)
   - HTTP endpoints under `/mcp/*` namespace
   - All endpoints use POST (even read operations) to support JSON request bodies
   - Handles JSON parsing/serialization and error responses
   - Delegates OmniFocus operations to AppleScript layer

2. **AppleScript Automation** (`scripts/*.applescript`)
   - Direct OmniFocus application control via AppleScript
   - Each script is standalone and returns JSON-formatted output
   - Scripts are invoked via `osascript` subprocess calls
   - Handle date formatting, escaping, and filtering logic

3. **Utility Layer** (`utils/`)
   - `applescript.py`: Subprocess wrapper for executing AppleScript files
   - `omnifocus.py`: Higher-level Python API (currently underutilized)

### Key Design Patterns

- **AppleScript as Source of Truth**: All OmniFocus data operations happen in AppleScript, not Python
- **JSON Communication**: AppleScripts construct JSON strings manually (no JSON libraries in AppleScript)
- **Error Propagation**: AppleScript errors → `AppleScriptError` → HTTP 500 responses
- **Filter Arguments**: `list_tasks.applescript` accepts optional filter arguments (flagged, due_soon, inbox)

## Development Commands

### Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run Server
```bash
# Development mode with auto-reload
uvicorn server:app --reload

# Production mode
uvicorn server:app --host 0.0.0.0 --port 8000
```

### Test AppleScripts Directly
```bash
# List all tasks
osascript scripts/list_tasks.applescript

# List with filter (flagged, due_soon, or inbox)
osascript scripts/list_tasks.applescript flagged

# Add task
osascript scripts/add_task.applescript "Task title" "Project name"

# Get projects
osascript scripts/get_projects.applescript

# Complete task by ID
osascript scripts/complete_task.applescript "task-id-here"
```

## API Endpoints

All endpoints use POST with JSON bodies:

- `GET /health` - Health check
- `POST /mcp/listTasks` - Optional body: `{"filter": "due_soon"|"flagged"|"inbox"}`
- `POST /mcp/summarizeTasks` - Groups tasks by project with counts (active, flagged, due_today, overdue)
- `POST /mcp/addTask` - Body: `{"title": "...", "project": "..."}`
- `POST /mcp/getProjects` - Returns list of OmniFocus projects
- `POST /mcp/completeTask` - Body: `{"task_id": "..."}`

## Important Implementation Details

### Date Handling
- AppleScript formats dates as ISO 8601: `YYYY-MM-DDTHH:MM:SS`
- Python parses with `datetime.fromisoformat()`
- Timezone handling: `summarizeTasks` uses UTC for comparisons

### JSON Construction in AppleScript
- Manual string concatenation (see `list_tasks.applescript:48-114`)
- Helper functions: `json_escape()`, `iso_date_string()`, `zero_pad()`
- Must escape: backslash, quotes, newlines

### Task Fields
- `id`: OmniFocus internal ID (text)
- `name`/`title`: Task name (both used interchangeably)
- `project`: Containing project name (empty string if none)
- `due`: ISO date string or empty string
- `flagged`: boolean
- `completed`: boolean
- `note`: Task notes/description

### Error Handling
- `AppleScriptError` raised when `osascript` fails or returns invalid JSON
- Server catches and returns HTTP 500 with error message
- Logging at INFO level for all operations

## File Locations

- AppleScripts: `scripts/*.applescript` (relative to server.py)
- Resolved via `Path(__file__).resolve().parent / "scripts" / "script_name.applescript"`
- Utils module: `utils/applescript.py` and `utils/omnifocus.py`

## Common Patterns

### Adding New Endpoints

1. Create AppleScript in `scripts/` that returns JSON
2. Add endpoint in `server.py`:
   ```python
   @app.post("/mcp/newEndpoint")
   async def new_endpoint(payload: dict):
       script_path = Path(__file__).resolve().parent / "scripts" / "new_script.applescript"
       try:
           output = run_script(script_path, *args)
           return json.loads(output)
       except AppleScriptError as exc:
           return JSONResponse(status_code=500, content={"error": str(exc)})
   ```

### AppleScript JSON Response Format
All scripts should return valid JSON. Example structure:
```applescript
set jsonText to "{\"tasks\":["
# ... build JSON string ...
set jsonText to jsonText & "]}"
return jsonText
```

## Dependencies

- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `requests` - HTTP client (may be unused)
- Python 3.11+
- macOS with OmniFocus installed
