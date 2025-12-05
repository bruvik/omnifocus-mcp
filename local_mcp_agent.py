from __future__ import annotations

import json
from typing import Any, Dict, List

import requests

# ------------------------------------------------------
# 1. Load MCP manifest (your server’s tool definitions)
# ------------------------------------------------------
def load_manifest(path: str = "manifest.json") -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def mcp_tools_to_ollama_tools(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert MCP manifest tools into Ollama-compatible tool definitions.
    """
    tools = []
    for tool in manifest.get("tools", []):
        params = tool.get("input_schema") or {"type": "object", "properties": {}, "required": []}
        tools.append(
            {
                "name": tool.get("name"),
                "description": tool.get("description", ""),
                "parameters": params,
            }
        )
    return tools


# ------------------------------------------------------
# 2. Send a message to the local model (Ollama example)
# ------------------------------------------------------
def call_local_model(
    messages: List[Dict[str, str]],
    model: str = "qwen2.5:7b-instruct",
    tools: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    Replace this function with your preferred local model backend.
    Below is an Ollama-compatible implementation.
    """
    payload: Dict[str, Any] = {"model": model, "messages": messages, "stream": False}
    if tools:
        payload["functions"] = tools

    try:
        resp = requests.post(
            "http://localhost:11434/api/chat",
            json=payload,
            timeout=180,
        )
    except requests.HTTPError as exc:
        print("Payload sent to Ollama (HTTPError):", json.dumps(payload, indent=2))
        raise exc
    except Exception:
        raise

    if resp.status_code >= 400:
        print("Payload sent to Ollama (status code >=400):", json.dumps(payload, indent=2))
        resp.raise_for_status()

    resp.raise_for_status()
    return resp.json()

# ------------------------------------------------------
# 3. Detect tool calls in model output
# ------------------------------------------------------
def extract_tool_call(response: Dict[str, Any]) -> Dict[str, Any] | None:
    """
    Expecting something like:
      { "message": { "function_call": { "name": ..., "arguments": "{...json...}" } } }
    """
    message = response.get("message") or response.get("messages", [{}])[0]
    if not message:
        return None

    fn_call = message.get("function_call")
    if not fn_call:
        return None

    args_raw = fn_call.get("arguments", "{}")
    try:
        args = json.loads(args_raw) if args_raw else {}
    except json.JSONDecodeError:
        args = {}

    return {"name": fn_call.get("name"), "arguments": args}

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

    if not isinstance(arguments, dict):
        raise RuntimeError(f"Tool arguments must be an object, got: {arguments}")

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
    tools_ollama = mcp_tools_to_ollama_tools(manifest)

    print("Loaded MCP tools:", list(tools.keys()))
    print(f"Using MCP server at: {base_url}")

    print("\nType your request (or 'quit').")

    conversation = [
        {
            "role": "system",
            "content": (
                "You are an MCP-compatible agent. When tools are provided, ALWAYS call a tool if "
                "the user request relates to that tool. Do not answer directly. Respond ONLY with "
                "a tool call in JSON format when appropriate."
            ),
        }
    ]

    while True:
        user_input = input("\nUser: ")
        if user_input.lower() in ("quit", "exit"):
            break

        conversation.append({"role": "user", "content": user_input})

        response = call_local_model(conversation, tools=tools_ollama)
        tool_call = extract_tool_call(response)

        if tool_call:
            tool_name = tool_call.get("name")
            arguments = tool_call.get("arguments", {})
            print(f"\n[Tool call detected: {tool_name}({arguments})]")

            try:
                result = call_mcp_server(tool_name, arguments, tools, base_url)  # type: ignore[arg-type]
            except Exception as exc:
                print(f"\nError calling tool {tool_name}: {exc}")
                continue

            conversation.append(
                {
                    "role": "tool",
                    "name": tool_name,
                    "content": json.dumps(result),
                }
            )

            response2 = call_local_model(conversation, tools=tools_ollama)
            assistant_msg = response2.get("message", {}).get("content")
            if assistant_msg:
                print("\nAssistant:", assistant_msg)
            else:
                print("\nNo assistant message after tool call. Raw response:", response2)
        else:
            print("\nNo tool_call found. Raw response for debugging:", response)


if __name__ == "__main__":
    mcp_conversation()
