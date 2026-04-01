"""Application configuration with environment variable validation."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


class AppConfig(BaseModel):
    """Validated application configuration loaded from environment variables."""

    # GitHub
    github_token: str = Field(description="GitHub personal access token")
    github_enterprise: str = Field(default="", description="Enterprise slug")
    github_org: str = Field(default="", description="Organization name")
    github_api_version: str = Field(default="2026-03-10", description="GitHub API version header")

    # Anthropic
    anthropic_api_key: str = Field(description="Anthropic API key for Claude")

    # App
    cache_ttl_hours: int = Field(default=6, ge=1, le=168)
    web_port: int = Field(default=8501, ge=1024, le=65535)
    log_level: str = Field(default="INFO")
    use_legacy_api: bool = Field(default=False)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        v = v.upper()
        if v not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            raise ValueError(f"Invalid log level: {v}")
        return v

    @field_validator("github_token")
    @classmethod
    def validate_github_token(cls, v: str) -> str:
        if not v or v.startswith("ghp_xxx"):
            raise ValueError(
                "GITHUB_TOKEN is not set or is still the placeholder value. "
                "Set a valid GitHub token with read:org or read:enterprise scope."
            )
        return v

    @field_validator("anthropic_api_key")
    @classmethod
    def validate_anthropic_key(cls, v: str) -> str:
        if not v or v.startswith("sk-ant-xxx"):
            raise ValueError(
                "ANTHROPIC_API_KEY is not set or is still the placeholder value. "
                "Set a valid Anthropic API key."
            )
        return v


def load_config() -> AppConfig:
    """Load and validate configuration from environment variables.

    Returns:
        Validated AppConfig instance.

    Raises:
        SystemExit: If required configuration is missing or invalid.
    """
    try:
        config = AppConfig(
            github_token=os.getenv("GITHUB_TOKEN", ""),
            github_enterprise=os.getenv("GITHUB_ENTERPRISE", ""),
            github_org=os.getenv("GITHUB_ORG", ""),
            github_api_version=os.getenv("GITHUB_API_VERSION", "2026-03-10"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            cache_ttl_hours=int(os.getenv("CACHE_TTL_HOURS", "6")),
            web_port=int(os.getenv("WEB_PORT", "8501")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            use_legacy_api=os.getenv("USE_LEGACY_API", "false").lower() == "true",
        )
    except Exception as e:
        logger.error("Configuration error: %s", e)
        raise SystemExit(f"❌ Configuration error: {e}") from e

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    return config
