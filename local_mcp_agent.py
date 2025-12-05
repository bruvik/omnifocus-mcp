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
            {"name": tool.get("name"), "description": tool.get("description", ""), "parameters": params}
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
    if fn_call:
        args_raw = fn_call.get("arguments", "{}")
        try:
            if isinstance(args_raw, dict):
                args = args_raw
            else:
                args = json.loads(args_raw) if args_raw else {}
        except json.JSONDecodeError:
            args = {}
        return {"name": fn_call.get("name"), "arguments": args}

    content = message.get("content")
    if isinstance(content, str):
        trimmed = content.strip()
        if trimmed.startswith("{") and "function_call" in trimmed:
            try:
                parsed = json.loads(trimmed)
                fn_call = parsed.get("function_call")
                if fn_call:
                    args_raw = fn_call.get("arguments", "{}")
                    try:
                        if isinstance(args_raw, dict):
                            args = args_raw
                        else:
                            args = json.loads(args_raw) if args_raw else {}
                    except json.JSONDecodeError:
                        args = {}
                    return {"name": fn_call.get("name"), "arguments": args}
            except Exception as exc:
                print("Failed to parse potential function_call JSON from content:", content)
                print("Parse error:", exc)

    return None

# ------------------------------------------------------
# 4. Call MCP server endpoint (based on manifest tool definition)
# ------------------------------------------------------
def call_mcp_server(
    tool_name: str,
    arguments: Dict[str, Any],
    tools: Dict[str, Dict[str, Any]],
    base_url: str,
):
    def normalize(name: str) -> str:
        return "".join(ch.lower() for ch in name if ch.isalnum() or ch == "_")

    if tool_name not in tools:
        # Attempt a normalized lookup (helps when model returns snake_case vs camelCase)
        norm = normalize(tool_name)
        candidates = {normalize(k): k for k in tools}
        if norm in candidates:
            tool_name = candidates[norm]
        else:
            valid_tools = ", ".join(sorted(tools.keys()))
            raise RuntimeError(
                f"Unknown tool: '{tool_name}'. Valid tools are: {valid_tools}"
            )

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

    # Build explicit tool list for system prompt
    tool_names_list = "\n".join([f"- {tool['name']}: {tool.get('description', '')}" for tool in tools_list])
    tool_schemas = "\n\n".join([
        f"{tool['name']}:\n  Parameters: {json.dumps(tool.get('input_schema', {}).get('properties', {}), indent=2)}"
        for tool in tools_list
    ])

    conversation = [
        {
            "role": "system",
            "content": (
                "You are an MCP-compatible agent with access to these EXACT functions (use these names exactly):\n\n"
                f"{tool_names_list}\n\n"
                "FUNCTION SCHEMAS:\n"
                f"{tool_schemas}\n\n"
                "CRITICAL RULES:\n"
                "1. Use the EXACT function names listed above (e.g., 'list_tasks' not 'listTasks')\n"
                "2. Only use parameters defined in the schema - DO NOT invent parameters\n"
                "3. When the user asks for something a function can perform, you MUST call that function\n"
                "4. Respond ONLY with a JSON object in this format:\n\n"
                "{\n  \"function_call\": {\n    \"name\": \"EXACT_FUNCTION_NAME\",\n    \"arguments\": {JSON_OBJECT_WITH_ONLY_DEFINED_PARAMETERS}\n  }\n}\n\n"
                "5. Do not answer normally when a function is relevant. Always call the appropriate function."
            ),
        }
    ]
    conversation.insert(
        1,
        {"role": "assistant", "content": "{\"function_call\": {\"name\": \"list_tasks\", \"arguments\": {}}}"},
    )

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

            actual_tool_name = tool_name  # Track which tool actually succeeded
            try:
                result = call_mcp_server(tool_name, arguments, tools, base_url)  # type: ignore[arg-type]
            except Exception as exc:
                error_msg = f"Error calling tool {tool_name}: {exc}"
                print(f"\n{error_msg}")

                # Feed error back to AI so it can self-correct
                conversation.append(
                    {
                        "role": "tool",
                        "name": tool_name,
                        "content": json.dumps({"error": str(exc)}),
                    }
                )

                # Let AI try again with the error context
                response2 = call_local_model(conversation, tools=tools_ollama)
                tool_call2 = extract_tool_call(response2)

                if tool_call2:
                    # Retry with corrected tool call
                    tool_name2 = tool_call2.get("name")
                    arguments2 = tool_call2.get("arguments", {})
                    print(f"\n[AI retrying with: {tool_name2}({arguments2})]")
                    try:
                        result = call_mcp_server(tool_name2, arguments2, tools, base_url)  # type: ignore[arg-type]
                        actual_tool_name = tool_name2  # Update to successful tool name
                    except Exception as exc2:
                        print(f"\nRetry also failed: {exc2}")
                        continue
                else:
                    assistant_msg = response2.get("message", {}).get("content")
                    if assistant_msg:
                        print("\nAssistant:", assistant_msg)
                    continue

            conversation.append(
                {
                    "role": "tool",
                    "name": actual_tool_name,
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
