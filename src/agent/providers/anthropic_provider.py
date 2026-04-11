"""Anthropic Claude LLM provider."""

from __future__ import annotations

import logging
from typing import Any

import anthropic

from ..llm_provider import LLMResponse, ToolCall

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-20250514"


class AnthropicProvider:
    """LLM provider backed by the Anthropic Messages API.

    Args:
        api_key: Anthropic API key.
        model: Model ID to use (default: claude-sonnet-4-20250514).
    """

    def __init__(self, api_key: str, model: str = "") -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model or DEFAULT_MODEL

    def call(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_tokens: int = 4096,
    ) -> LLMResponse:
        raw = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages,
            tools=tools,
        )

        # Normalize response
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        for block in raw.content:
            if hasattr(block, "type"):
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_calls.append(ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input,
                    ))

        stop = "tool_use" if raw.stop_reason == "tool_use" else "end_turn"

        return LLMResponse(
            text="\n".join(text_parts),
            tool_calls=tool_calls,
            stop_reason=stop,
            raw=raw,
        )

    def serialize_assistant(self, response: LLMResponse) -> dict[str, Any]:
        """Serialize assistant response into Anthropic message format."""
        content: list[dict[str, Any]] = []
        for block in response.raw.content:
            if hasattr(block, "type"):
                if block.type == "text":
                    content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
        return {"role": "assistant", "content": content}

    def format_tool_results(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """Format tool results as an Anthropic user message with tool_result blocks."""
        blocks = []
        for r in results:
            block: dict[str, Any] = {
                "type": "tool_result",
                "tool_use_id": r["tool_call_id"],
                "content": r["content"],
            }
            if r.get("is_error"):
                block["is_error"] = True
            blocks.append(block)
        return {"role": "user", "content": blocks}
