# OmniFocus MCP Server

FastAPI server that exposes OmniFocus tasks to Model Context Protocol (MCP) hosts via AppleScript.

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

## Endpoints

- `GET /health` – simple healthcheck
- `GET /mcp/listTasks` – returns `{"tasks": [...]}` from `scripts/list_tasks.applescript`
- `POST /mcp/addTask` – body `{"title": "...", "project": "optional"}`; delegates to `scripts/add_task.applescript`

## AppleScript helpers

The server shells out to `osascript` to call the scripts in `scripts/`. You can test them directly:

```bash
osascript scripts/list_tasks.applescript
osascript scripts/add_task.applescript "Pick up milk" "Home"
```
