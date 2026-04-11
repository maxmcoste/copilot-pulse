"""Convert tool schemas and messages between Anthropic and OpenAI formats."""

from __future__ import annotations

import json
from typing import Any


def anthropic_to_openai_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Anthropic tool definitions to OpenAI function-calling format.

    Anthropic: {"name", "description", "input_schema": {…}}
    OpenAI:    {"type": "function", "function": {"name", "description", "parameters": {…}}}
    """
    converted = []
    for tool in tools:
        converted.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {"type": "object", "properties": {}}),
            },
        })
    return converted


def anthropic_to_openai_messages(
    system_prompt: str,
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert Anthropic-format message history to OpenAI-format messages.

    Handles:
    - System prompt → {"role": "system", "content": ...}
    - Plain text messages → passed through
    - Assistant messages with tool_use blocks → {"role": "assistant", "tool_calls": [...]}
    - User messages with tool_result blocks → multiple {"role": "tool", ...} messages
    """
    out: list[dict[str, Any]] = []

    if system_prompt:
        out.append({"role": "system", "content": system_prompt})

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        # Plain string content — pass through
        if isinstance(content, str):
            out.append({"role": role, "content": content})
            continue

        # List of content blocks (Anthropic format)
        if isinstance(content, list):
            if role == "assistant":
                out.append(_convert_assistant_blocks(content))
            elif role == "user":
                out.extend(_convert_user_blocks(content))
            else:
                # Fallback: join text blocks
                text = " ".join(
                    b.get("text", "") for b in content if b.get("type") == "text"
                )
                out.append({"role": role, "content": text or ""})

    return out


def _convert_assistant_blocks(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    """Convert Anthropic assistant content blocks to OpenAI format."""
    text_parts = []
    tool_calls = []

    for block in blocks:
        if block.get("type") == "text":
            text_parts.append(block["text"])
        elif block.get("type") == "tool_use":
            tool_calls.append({
                "id": block["id"],
                "type": "function",
                "function": {
                    "name": block["name"],
                    "arguments": json.dumps(block.get("input", {})),
                },
            })

    msg: dict[str, Any] = {"role": "assistant"}
    msg["content"] = "\n".join(text_parts) if text_parts else None
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return msg


def _convert_user_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Anthropic user content blocks (including tool_result) to OpenAI format."""
    out: list[dict[str, Any]] = []

    for block in blocks:
        if block.get("type") == "tool_result":
            out.append({
                "role": "tool",
                "tool_call_id": block["tool_use_id"],
                "content": block.get("content", ""),
            })
        elif block.get("type") == "text":
            out.append({"role": "user", "content": block["text"]})
        else:
            # Unknown block — skip or pass as text
            text = block.get("text") or block.get("content") or ""
            if text:
                out.append({"role": "user", "content": str(text)})

    return out
