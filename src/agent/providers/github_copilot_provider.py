"""GitHub Copilot / GitHub Models LLM provider (OpenAI-compatible API)."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from ..llm_provider import LLMResponse, ToolCall
from .schema_converter import anthropic_to_openai_messages, anthropic_to_openai_tools

logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = "https://models.github.com/chat/completions"
DEFAULT_MODEL = "gpt-4o"


class GitHubCopilotProvider:
    """LLM provider backed by the GitHub Models OpenAI-compatible API.

    Uses the user's GITHUB_TOKEN for authentication.

    Args:
        github_token: GitHub personal access token.
        model: Model ID (default: gpt-4o).
        endpoint: Chat completions endpoint URL.
    """

    def __init__(
        self,
        github_token: str,
        model: str = "",
        endpoint: str = "",
    ) -> None:
        self._token = github_token
        self._model = model or DEFAULT_MODEL
        self._endpoint = endpoint or DEFAULT_ENDPOINT
        self._http = httpx.Client(
            timeout=120.0,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
        )

    def call(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_tokens: int = 4096,
    ) -> LLMResponse:
        # Convert from Anthropic format to OpenAI format
        oai_messages = anthropic_to_openai_messages(system_prompt, messages)
        oai_tools = anthropic_to_openai_tools(tools)

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": oai_messages,
            "max_tokens": max_tokens,
        }
        if oai_tools:
            payload["tools"] = oai_tools

        resp = self._http.post(self._endpoint, json=payload)
        resp.raise_for_status()
        data = resp.json()

        return self._parse_response(data)

    def _parse_response(self, data: dict[str, Any]) -> LLMResponse:
        """Parse OpenAI chat completion response into normalized LLMResponse."""
        choice = data["choices"][0]
        message = choice["message"]
        finish_reason = choice.get("finish_reason", "stop")

        text = message.get("content") or ""
        tool_calls: list[ToolCall] = []

        if message.get("tool_calls"):
            for tc in message["tool_calls"]:
                func = tc["function"]
                try:
                    args = json.loads(func["arguments"])
                except (json.JSONDecodeError, TypeError):
                    args = {}
                tool_calls.append(ToolCall(
                    id=tc["id"],
                    name=func["name"],
                    arguments=args,
                ))

        stop = "tool_use" if finish_reason in ("tool_calls", "function_call") else "end_turn"

        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            stop_reason=stop,
            raw=data,
        )

    def serialize_assistant(self, response: LLMResponse) -> dict[str, Any]:
        """Serialize assistant response into Anthropic-compatible format for history.

        We store history in Anthropic format internally; conversion to OpenAI
        happens in call() via anthropic_to_openai_messages.
        """
        content: list[dict[str, Any]] = []
        if response.text:
            content.append({"type": "text", "text": response.text})
        for tc in response.tool_calls:
            content.append({
                "type": "tool_use",
                "id": tc.id,
                "name": tc.name,
                "input": tc.arguments,
            })
        return {"role": "assistant", "content": content}

    def format_tool_results(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """Format tool results as Anthropic-style user message with tool_result blocks.

        History is stored in Anthropic format; conversion happens in call().
        """
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

    def close(self) -> None:
        """Close the HTTP client."""
        self._http.close()
