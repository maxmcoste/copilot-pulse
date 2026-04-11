"""Tests for the LLM provider abstraction layer."""

from __future__ import annotations

import json

import pytest

from src.agent.llm_provider import LLMResponse, ToolCall
from src.agent.providers.schema_converter import (
    anthropic_to_openai_messages,
    anthropic_to_openai_tools,
)


class TestSchemaConverter:
    """Test Anthropic → OpenAI tool schema conversion."""

    def test_converts_all_tools(self) -> None:
        from src.agent.tools_schema import TOOLS

        oai_tools = anthropic_to_openai_tools(TOOLS)
        assert len(oai_tools) == len(TOOLS)

    def test_tool_structure(self) -> None:
        tools = [
            {
                "name": "my_tool",
                "description": "Does things",
                "input_schema": {
                    "type": "object",
                    "properties": {"x": {"type": "string"}},
                    "required": ["x"],
                },
            }
        ]
        result = anthropic_to_openai_tools(tools)
        assert len(result) == 1
        t = result[0]
        assert t["type"] == "function"
        assert t["function"]["name"] == "my_tool"
        assert t["function"]["description"] == "Does things"
        assert t["function"]["parameters"]["properties"]["x"]["type"] == "string"
        assert t["function"]["parameters"]["required"] == ["x"]

    def test_empty_input_schema(self) -> None:
        tools = [{"name": "t", "description": "d"}]
        result = anthropic_to_openai_tools(tools)
        assert result[0]["function"]["parameters"] == {"type": "object", "properties": {}}


class TestMessageConverter:
    """Test Anthropic → OpenAI message history conversion."""

    def test_system_prompt_injected(self) -> None:
        msgs = anthropic_to_openai_messages("You are a bot.", [])
        assert msgs[0] == {"role": "system", "content": "You are a bot."}

    def test_plain_text_messages(self) -> None:
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        msgs = anthropic_to_openai_messages("sys", history)
        assert msgs[1] == {"role": "user", "content": "Hello"}
        assert msgs[2] == {"role": "assistant", "content": "Hi there"}

    def test_assistant_tool_use_blocks(self) -> None:
        history = [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Let me check."},
                    {
                        "type": "tool_use",
                        "id": "call_1",
                        "name": "get_metrics",
                        "input": {"org": "myorg"},
                    },
                ],
            }
        ]
        msgs = anthropic_to_openai_messages("", history)
        asst = msgs[0]
        assert asst["role"] == "assistant"
        assert asst["content"] == "Let me check."
        assert len(asst["tool_calls"]) == 1
        tc = asst["tool_calls"][0]
        assert tc["id"] == "call_1"
        assert tc["function"]["name"] == "get_metrics"
        assert json.loads(tc["function"]["arguments"]) == {"org": "myorg"}

    def test_user_tool_result_blocks(self) -> None:
        history = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "call_1",
                        "content": '{"count": 42}',
                    }
                ],
            }
        ]
        msgs = anthropic_to_openai_messages("", history)
        assert msgs[0]["role"] == "tool"
        assert msgs[0]["tool_call_id"] == "call_1"
        assert msgs[0]["content"] == '{"count": 42}'

    def test_multiple_tool_results(self) -> None:
        history = [
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "c1", "content": "r1"},
                    {"type": "tool_result", "tool_use_id": "c2", "content": "r2"},
                ],
            }
        ]
        msgs = anthropic_to_openai_messages("", history)
        assert len(msgs) == 2
        assert msgs[0]["tool_call_id"] == "c1"
        assert msgs[1]["tool_call_id"] == "c2"


class TestLLMResponse:
    """Test the normalized LLM response type."""

    def test_has_tool_calls_true(self) -> None:
        r = LLMResponse(
            stop_reason="tool_use",
            tool_calls=[ToolCall(id="1", name="t", arguments={})],
        )
        assert r.has_tool_calls is True

    def test_has_tool_calls_false_no_calls(self) -> None:
        r = LLMResponse(stop_reason="tool_use", tool_calls=[])
        assert r.has_tool_calls is False

    def test_has_tool_calls_false_end_turn(self) -> None:
        r = LLMResponse(
            stop_reason="end_turn",
            tool_calls=[ToolCall(id="1", name="t", arguments={})],
        )
        assert r.has_tool_calls is False

    def test_defaults(self) -> None:
        r = LLMResponse()
        assert r.text == ""
        assert r.tool_calls == []
        assert r.stop_reason == "end_turn"
        assert r.has_tool_calls is False


class TestProviderFactory:
    """Test provider creation."""

    def test_unknown_provider_raises(self) -> None:
        from unittest.mock import MagicMock

        config = MagicMock()
        config.llm_provider = "unknown"
        from src.agent.providers import create_provider

        with pytest.raises(ValueError, match="Unknown LLM provider"):
            create_provider(config)

    def test_anthropic_provider_created(self) -> None:
        from unittest.mock import MagicMock

        config = MagicMock()
        config.llm_provider = "anthropic"
        config.anthropic_api_key = "sk-ant-test123"
        config.llm_model = ""

        from src.agent.providers import create_provider
        from src.agent.providers.anthropic_provider import AnthropicProvider

        provider = create_provider(config)
        assert isinstance(provider, AnthropicProvider)

    def test_github_copilot_provider_created(self) -> None:
        from unittest.mock import MagicMock

        config = MagicMock()
        config.llm_provider = "github-copilot"
        config.github_token = "ghp_test123"
        config.llm_model = "gpt-4o"
        config.llm_endpoint = ""

        from src.agent.providers import create_provider
        from src.agent.providers.github_copilot_provider import GitHubCopilotProvider

        provider = create_provider(config)
        assert isinstance(provider, GitHubCopilotProvider)


class TestAnthropicProviderSerialization:
    """Test AnthropicProvider serialize/format methods."""

    def test_format_tool_results(self) -> None:
        from src.agent.providers.anthropic_provider import AnthropicProvider

        provider = AnthropicProvider.__new__(AnthropicProvider)
        results = [
            {"tool_call_id": "c1", "content": '{"ok": true}'},
            {"tool_call_id": "c2", "content": '{"error": "fail"}', "is_error": True},
        ]
        msg = provider.format_tool_results(results)
        assert msg["role"] == "user"
        blocks = msg["content"]
        assert len(blocks) == 2
        assert blocks[0]["type"] == "tool_result"
        assert blocks[0]["tool_use_id"] == "c1"
        assert blocks[1]["is_error"] is True


class TestGitHubCopilotProviderSerialization:
    """Test GitHubCopilotProvider serialize/format methods."""

    def test_serialize_assistant_text_only(self) -> None:
        from src.agent.providers.github_copilot_provider import GitHubCopilotProvider

        provider = GitHubCopilotProvider.__new__(GitHubCopilotProvider)
        response = LLMResponse(text="Hello world", stop_reason="end_turn")
        msg = provider.serialize_assistant(response)
        assert msg["role"] == "assistant"
        assert msg["content"] == [{"type": "text", "text": "Hello world"}]

    def test_serialize_assistant_with_tool_calls(self) -> None:
        from src.agent.providers.github_copilot_provider import GitHubCopilotProvider

        provider = GitHubCopilotProvider.__new__(GitHubCopilotProvider)
        response = LLMResponse(
            text="",
            tool_calls=[ToolCall(id="tc1", name="my_tool", arguments={"x": 1})],
            stop_reason="tool_use",
        )
        msg = provider.serialize_assistant(response)
        assert msg["content"][0]["type"] == "tool_use"
        assert msg["content"][0]["name"] == "my_tool"

    def test_parse_openai_response(self) -> None:
        from src.agent.providers.github_copilot_provider import GitHubCopilotProvider

        provider = GitHubCopilotProvider.__new__(GitHubCopilotProvider)
        raw_data = {
            "choices": [
                {
                    "message": {
                        "content": "Here are the results.",
                        "tool_calls": [
                            {
                                "id": "call_abc",
                                "type": "function",
                                "function": {
                                    "name": "get_metrics",
                                    "arguments": '{"org": "test"}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        }
        resp = provider._parse_response(raw_data)
        assert resp.text == "Here are the results."
        assert resp.stop_reason == "tool_use"
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0].name == "get_metrics"
        assert resp.tool_calls[0].arguments == {"org": "test"}

    def test_parse_text_only_response(self) -> None:
        from src.agent.providers.github_copilot_provider import GitHubCopilotProvider

        provider = GitHubCopilotProvider.__new__(GitHubCopilotProvider)
        raw_data = {
            "choices": [
                {
                    "message": {"content": "Just text.", "tool_calls": None},
                    "finish_reason": "stop",
                }
            ]
        }
        resp = provider._parse_response(raw_data)
        assert resp.text == "Just text."
        assert resp.stop_reason == "end_turn"
        assert resp.tool_calls == []


class TestConfigValidation:
    """Test config validation for LLM providers."""

    def test_anthropic_requires_key(self) -> None:
        from src.config import AppConfig

        with pytest.raises(Exception, match="ANTHROPIC_API_KEY"):
            AppConfig(
                github_token="ghp_valid123",
                llm_provider="anthropic",
                anthropic_api_key="",
            )

    def test_github_copilot_no_anthropic_key_needed(self) -> None:
        from src.config import AppConfig

        config = AppConfig(
            github_token="ghp_valid123",
            llm_provider="github-copilot",
            anthropic_api_key="",
        )
        assert config.llm_provider == "github-copilot"

    def test_invalid_provider_rejected(self) -> None:
        from src.config import AppConfig

        with pytest.raises(Exception, match="Invalid LLM_PROVIDER"):
            AppConfig(
                github_token="ghp_valid123",
                llm_provider="openai",
            )
