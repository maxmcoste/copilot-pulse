"""Application configuration with environment variable validation."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

# Runtime-writable settings file (LLM overrides only — no GitHub auth).
SETTINGS_FILE = Path(__file__).resolve().parent.parent / "settings.json"

# Keys stored in settings.json (subset of AppConfig).
# NOTE: llm_github_token is separate from github_token (used for API auth).
#       It is ONLY passed to the GitHub Copilot LLM provider and never touches
#       the GitHub App / PAT authentication used for Copilot usage API calls.
_SETTINGS_KEYS = {"llm_provider", "anthropic_api_key", "llm_model", "llm_endpoint", "llm_github_token"}


def load_settings_file() -> dict:
    """Return persisted LLM settings, or {} if the file does not exist."""
    try:
        if SETTINGS_FILE.is_file():
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            return {k: v for k, v in data.items() if k in _SETTINGS_KEYS}
    except Exception as exc:
        logger.warning("Could not read %s: %s", SETTINGS_FILE, exc)
    return {}


def save_settings_file(data: dict) -> None:
    """Persist LLM settings to settings.json (atomic write)."""
    filtered = {k: v for k, v in data.items() if k in _SETTINGS_KEYS}
    tmp = SETTINGS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(filtered, indent=2), encoding="utf-8")
    tmp.replace(SETTINGS_FILE)


class AppConfig(BaseModel):
    """Validated application configuration loaded from environment variables."""

    # GitHub auth — either a PAT or a GitHub App installation.
    github_token: str = Field(default="", description="GitHub personal access token")
    github_app_id: int | None = Field(default=None, description="GitHub App numeric ID")
    github_app_installation_id: int | None = Field(
        default=None, description="GitHub App installation ID on the target org"
    )
    github_app_private_key: str | None = Field(
        default=None, description="GitHub App private key (inline PEM)"
    )
    github_app_private_key_path: str | None = Field(
        default=None, description="Path to GitHub App private key PEM file"
    )
    auth_mode: str = Field(
        default="pat", description="Resolved auth mode: 'pat' or 'app'"
    )

    github_enterprise: str = Field(default="", description="Enterprise slug")
    github_org: str = Field(default="", description="Organization name")
    github_api_version: str = Field(default="2026-03-10", description="GitHub API version header")

    # LLM
    llm_provider: str = Field(
        default="anthropic",
        description="LLM provider: 'anthropic' or 'github-copilot'",
    )
    llm_model: str = Field(
        default="",
        description="Model override (empty = provider default)",
    )
    llm_endpoint: str = Field(
        default="",
        description="Custom endpoint URL for the LLM provider",
    )
    anthropic_api_key: str = Field(
        default="",
        description="Anthropic API key for Claude (required when llm_provider=anthropic)",
    )
    llm_github_token: str = Field(
        default="",
        description="GitHub PAT used exclusively for the GitHub Copilot LLM provider. "
                    "Never used for GitHub API authentication.",
    )

    # App
    cache_ttl_hours: int = Field(default=6, ge=1, le=168)
    web_port: int = Field(default=8501, ge=1024, le=65535)
    log_level: str = Field(default="INFO")
    use_legacy_api: bool = Field(default=False)
    org_structure_file: str = Field(default="", description="Path to org structure Excel file")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        v = v.upper()
        if v not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            raise ValueError(f"Invalid log level: {v}")
        return v

    @model_validator(mode="after")
    def validate_github_auth(self) -> AppConfig:
        """Resolve and validate GitHub auth mode (PAT vs GitHub App)."""
        has_app = (
            self.github_app_id is not None
            and self.github_app_installation_id is not None
            and (self.github_app_private_key or self.github_app_private_key_path)
        )
        has_pat = bool(self.github_token) and not self.github_token.startswith("ghp_xxx")

        if has_app:
            # App auth wins if fully configured.
            object.__setattr__(self, "auth_mode", "app")
            if self.github_app_private_key_path:
                from pathlib import Path as _P

                if not _P(self.github_app_private_key_path).is_file():
                    raise ValueError(
                        f"GITHUB_APP_PRIVATE_KEY_PATH does not exist: "
                        f"{self.github_app_private_key_path}"
                    )
        elif has_pat:
            object.__setattr__(self, "auth_mode", "pat")
        else:
            raise ValueError(
                "No GitHub authentication configured. Set either GITHUB_TOKEN "
                "(PAT) or the GitHub App trio "
                "(GITHUB_APP_ID, GITHUB_APP_INSTALLATION_ID, and "
                "GITHUB_APP_PRIVATE_KEY or GITHUB_APP_PRIVATE_KEY_PATH)."
            )
        return self

    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in ("anthropic", "github-copilot"):
            raise ValueError(
                f"Invalid LLM_PROVIDER: '{v}'. Must be 'anthropic' or 'github-copilot'."
            )
        return v

    @model_validator(mode="after")
    def validate_provider_keys(self) -> AppConfig:
        if self.llm_provider == "anthropic":
            if not self.anthropic_api_key or self.anthropic_api_key.startswith("sk-ant-xxx"):
                raise ValueError(
                    "ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic. "
                    "Set a valid Anthropic API key or switch to LLM_PROVIDER=github-copilot."
                )
        elif self.llm_provider == "github-copilot":
            # llm_github_token is the dedicated PAT for the Copilot LLM endpoint.
            # It is completely separate from github_token (GitHub API auth).
            if not self.llm_github_token:
                raise ValueError(
                    "LLM_PROVIDER=github-copilot requires LLM_GITHUB_TOKEN (a Personal "
                    "Access Token with Copilot access). This is separate from GITHUB_TOKEN "
                    "and does not affect GitHub API authentication. "
                    "Set LLM_GITHUB_TOKEN in .env, or use the Settings page, "
                    "or switch LLM_PROVIDER=anthropic."
                )
        return self


def load_config() -> AppConfig:
    """Load and validate configuration from environment variables.

    Returns:
        Validated AppConfig instance.

    Raises:
        SystemExit: If required configuration is missing or invalid.
    """
    # settings.json overrides env vars for LLM-specific keys.
    _overrides = load_settings_file()

    def _get(key: str, env_var: str, default: str = "") -> str:
        v = _overrides.get(key, "")
        # Discard masked values written by the UI (contain the bullet masking char).
        if v and "•" in v:
            v = ""
        return v or os.getenv(env_var, default)

    try:
        app_id_env = os.getenv("GITHUB_APP_ID", "").strip()
        inst_id_env = os.getenv("GITHUB_APP_INSTALLATION_ID", "").strip()
        config = AppConfig(
            github_token=os.getenv("GITHUB_TOKEN", ""),
            github_app_id=int(app_id_env) if app_id_env else None,
            github_app_installation_id=int(inst_id_env) if inst_id_env else None,
            github_app_private_key=os.getenv("GITHUB_APP_PRIVATE_KEY") or None,
            github_app_private_key_path=os.getenv("GITHUB_APP_PRIVATE_KEY_PATH") or None,
            github_enterprise=os.getenv("GITHUB_ENTERPRISE", ""),
            github_org=os.getenv("GITHUB_ORG", ""),
            github_api_version=os.getenv("GITHUB_API_VERSION", "2026-03-10"),
            llm_provider=_get("llm_provider", "LLM_PROVIDER", "anthropic"),
            llm_model=_get("llm_model", "LLM_MODEL", ""),
            llm_endpoint=_get("llm_endpoint", "LLM_ENDPOINT", ""),
            anthropic_api_key=_get("anthropic_api_key", "ANTHROPIC_API_KEY", ""),
            llm_github_token=_get("llm_github_token", "LLM_GITHUB_TOKEN", ""),
            cache_ttl_hours=int(os.getenv("CACHE_TTL_HOURS", "6")),
            web_port=int(os.getenv("WEB_PORT", "8501")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            use_legacy_api=os.getenv("USE_LEGACY_API", "false").lower() == "true",
            org_structure_file=os.getenv("ORG_STRUCTURE_FILE", ""),
        )
    except Exception as e:
        logger.error("Configuration error: %s", e)
        raise SystemExit(f"Configuration error: {e}") from e

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    return config
