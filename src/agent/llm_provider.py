"""LLM provider abstraction — normalized types and protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolCall:
    """A normalized tool call extracted from an LLM response."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """Normalized LLM response independent of provider."""

    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"  # "end_turn" or "tool_use"
    raw: Any = None

    @property
    def has_tool_calls(self) -> bool:
        return self.stop_reason == "tool_use" and len(self.tool_calls) > 0


class LLMProvider(Protocol):
    """Protocol for LLM provider implementations."""

    def call(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Send a message to the LLM and return a normalized response.

        Args:
            system_prompt: System-level instructions.
            messages: Conversation history in Anthropic message format.
            tools: Tool definitions in Anthropic format.
            max_tokens: Maximum tokens in the response.

        Returns:
            Normalized LLMResponse.
        """
        ...

    def serialize_assistant(self, response: LLMResponse) -> dict[str, Any]:
        """Serialize an assistant response for inclusion in message history.

        Args:
            response: The LLM response to serialize.

        Returns:
            A dict suitable for appending to the messages list.
        """
        ...

    def format_tool_results(
        self, results: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Format tool execution results for the next API call.

        Args:
            results: List of dicts with 'tool_call_id', 'content', and optionally 'is_error'.

        Returns:
            A message dict suitable for appending to the messages list.
        """
        ...
