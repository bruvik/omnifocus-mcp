# OmniFocus MCP Server

FastAPI server that surfaces OmniFocus inbox tasks through a simple MCP-friendly API backed by AppleScript.

## Prerequisites

- macOS with OmniFocus installed
- Python 3.11+

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the server

```bash
uvicorn server:app --reload
```

### Endpoints

- `GET /tasks` – list inbox tasks (id, name, completed)
- `POST /tasks` – create a new inbox task: body `{"name": "Do the thing", "note": "optional note"}`

## AppleScript helpers

The server shells out to `osascript` to call the AppleScript files in `scripts/`. You can test them directly, for example:

```bash
osascript scripts/add_task.applescript "Read docs" "Add more detail here"
osascript scripts/list_tasks.applescript
```
