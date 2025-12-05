from __future__ import annotations

import json
from typing import Any, Dict, List

import requests

# ------------------------------------------------------
# 1. Load MCP manifest (your server’s tool definitions)
# ------------------------------------------------------
def load_manifest(path: str = "omnifocus-mcp.json") -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ------------------------------------------------------
# 2. Send a message to the local model (Ollama example)
# ------------------------------------------------------
def call_local_model(messages: List[Dict[str, str]], model: str = "llama3:latest") -> Dict[str, Any]:
    """
    Replace this function with your preferred local model backend.
    Below is an Ollama-compatible implementation.
    """
    resp = requests.post(
        "http://localhost:11434/api/chat",
        json={"model": model, "messages": messages, "stream": False},
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()

# ------------------------------------------------------
# 3. Detect tool calls in model output
# ------------------------------------------------------
def extract_tool_call(response: Dict[str, Any]) -> Dict[str, Any] | None:
    """
    Expecting something like:
      { "message": { "tool_call": { "name": ..., "arguments": {...} } } }
    """
    message = response.get("message") or response.get("messages", [{}])[0]
    if not message:
        return None

    return message.get("tool_call")

# ------------------------------------------------------
# 4. Call MCP server endpoint (based on manifest tool definition)
# ------------------------------------------------------
def call_mcp_server(
    tool_name: str,
    arguments: Dict[str, Any],
    tools: Dict[str, Dict[str, Any]],
    base_url: str,
):
    if tool_name not in tools:
        raise RuntimeError(f"Unknown tool: {tool_name}")

    tool_def = tools[tool_name]
    method = tool_def.get("method", "POST").upper()
    path = tool_def.get("path") or f"/mcp/{tool_name}"

    url = base_url.rstrip("/") + path

    if method == "GET":
        resp = requests.get(url, params=arguments, timeout=60)
    else:
        resp = requests.post(url, json=arguments, timeout=60)

    resp.raise_for_status()
    return resp.json()

# ------------------------------------------------------
# 5. Main interaction loop
# ------------------------------------------------------
def mcp_conversation():
    manifest = load_manifest()
    base_url = manifest.get("base_url", "http://localhost:8000")
    tools_list = manifest.get("tools", [])
    tools = {tool["name"]: tool for tool in tools_list}

    print("Loaded MCP tools:", list(tools.keys()))
    print(f"Using MCP server at: {base_url}")

    print("\nType your request (or 'quit').")

    conversation = [
        {"role": "system", "content": "You are an MCP-capable assistant. Use the provided tools when appropriate."}
    ]

    while True:
        user_input = input("\nUser: ")
        if user_input.lower() in ("quit", "exit"):
            break

        conversation.append({"role": "user", "content": user_input})

        # send to local model
        response = call_local_model(conversation)
        msg = response["message"]["content"]
        tool_call = extract_tool_call(response)

        if tool_call:
            tool_name = tool_call["name"]
            arguments = tool_call.get("arguments", {})
            print(f"\n[Tool call detected: {tool_name}({arguments})]")

            result = call_mcp_server(tool_name, arguments, tools, base_url)

            # feed tool result back to model
            conversation.append(
                {
                    "role": "tool",
                    "name": tool_name,
                    "content": json.dumps(result),
                }
            )

            # ask model to continue reasoning
            response2 = call_local_model(conversation)
            print("\nAssistant:", response2["message"]["content"])
        else:
            print("\nAssistant:", msg)


if __name__ == "__main__":
    mcp_conversation()
