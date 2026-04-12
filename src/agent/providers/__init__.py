"""LLM provider factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..llm_provider import LLMProvider

if TYPE_CHECKING:
    from ...config import AppConfig


def create_provider_from_settings(
    *,
    llm_provider: str,
    anthropic_api_key: str = "",
    github_token: str = "",
    llm_model: str = "",
    llm_endpoint: str = "",
) -> LLMProvider:
    """Create an LLM provider directly from named parameters.

    Used for runtime hot-swapping from the settings page without
    reconstructing the full AppConfig.
    """
    match llm_provider:
        case "anthropic":
            from .anthropic_provider import AnthropicProvider
            return AnthropicProvider(api_key=anthropic_api_key, model=llm_model)
        case "github-copilot":
            from .github_copilot_provider import GitHubCopilotProvider
            return GitHubCopilotProvider(
                github_token=github_token, model=llm_model, endpoint=llm_endpoint
            )
        case _:
            raise ValueError(f"Unknown LLM provider: '{llm_provider}'")


def create_provider(config: AppConfig) -> LLMProvider:
    """Create an LLM provider based on configuration.

    Args:
        config: Application configuration with llm_provider, llm_model, etc.

    Returns:
        An LLMProvider instance.

    Raises:
        ValueError: If the provider name is unknown.
    """
    match config.llm_provider:
        case "anthropic":
            from .anthropic_provider import AnthropicProvider

            return AnthropicProvider(
                api_key=config.anthropic_api_key,
                model=config.llm_model,
            )
        case "github-copilot":
            from .github_copilot_provider import GitHubCopilotProvider

            return GitHubCopilotProvider(
                github_token=config.llm_github_token,  # dedicated LLM token, not the API auth token
                model=config.llm_model,
                endpoint=config.llm_endpoint,
            )
        case _:
            raise ValueError(
                f"Unknown LLM provider: '{config.llm_provider}'. "
                f"Valid options: 'anthropic', 'github-copilot'"
            )
