"""GitHub authentication helpers.

Supports two modes:

- ``GitHubAuth``: static personal access token (PAT) / fine-grained token.
- ``GitHubAppAuth``: GitHub App installation auth. Mints a short-lived JWT from
  the App's private key, exchanges it for an installation access token via
  ``POST /app/installations/{id}/access_tokens``, caches the token in-memory,
  and refreshes it automatically shortly before expiry.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import httpx
import jwt

if TYPE_CHECKING:
    from ..config import AppConfig

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
# Refresh installation token when this close (or closer) to expiry.
_TOKEN_REFRESH_SKEW = timedelta(seconds=60)
# GitHub allows JWTs with a max 10-minute lifetime; use 9 min to stay safe.
_JWT_LIFETIME = timedelta(minutes=9)


class GitHubAuth(httpx.Auth):
    """httpx Auth handler for GitHub API token (PAT) authentication."""

    def __init__(self, token: str, api_version: str = "2026-03-10") -> None:
        self.token = token
        self.api_version = api_version

    def auth_flow(self, request: httpx.Request):
        request.headers["Authorization"] = f"Bearer {self.token}"
        request.headers["Accept"] = "application/vnd.github+json"
        request.headers["X-GitHub-Api-Version"] = self.api_version
        yield request


class GitHubAppAuth(httpx.Auth):
    """httpx Auth handler for GitHub App installation authentication.

    Generates a JWT signed with the App's RSA private key, exchanges it for an
    installation access token, and transparently refreshes the token before it
    expires.

    Args:
        app_id: Numeric GitHub App ID.
        installation_id: Installation ID for the target org.
        private_key_pem: RSA private key in PEM format.
        api_version: GitHub API version header value.
    """

    # httpx needs to know whether the auth_flow will re-read the request body
    # on re-issue; we never do.
    requires_request_body = False

    def __init__(
        self,
        app_id: int,
        installation_id: int,
        private_key_pem: str,
        api_version: str = "2026-03-10",
    ) -> None:
        self.app_id = app_id
        self.installation_id = installation_id
        self._private_key = private_key_pem
        self.api_version = api_version
        self._token: str | None = None
        self._token_expires_at: datetime | None = None
        self._lock = asyncio.Lock()

    # -- JWT / installation token -------------------------------------------------

    def _generate_jwt(self) -> str:
        now = datetime.now(tz=timezone.utc)
        payload = {
            # Backdate 60s to tolerate clock drift (per GitHub docs).
            "iat": int((now - timedelta(seconds=60)).timestamp()),
            "exp": int((now + _JWT_LIFETIME).timestamp()),
            "iss": str(self.app_id),
        }
        return jwt.encode(payload, self._private_key, algorithm="RS256")

    def _token_expiring_soon(self) -> bool:
        if self._token is None or self._token_expires_at is None:
            return True
        return datetime.now(tz=timezone.utc) + _TOKEN_REFRESH_SKEW >= self._token_expires_at

    async def _refresh_installation_token(self) -> None:
        """POST /app/installations/{id}/access_tokens and cache the result."""
        jwt_token = self._generate_jwt()
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.api_version,
        }
        url = f"{GITHUB_API_BASE}/app/installations/{self.installation_id}/access_tokens"

        # Standalone client so we don't recurse through our own auth flow.
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            resp = await client.post(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        self._token = data["token"]
        # expires_at is ISO8601, e.g. "2026-04-09T12:34:56Z"
        expires_raw: str = data["expires_at"]
        self._token_expires_at = datetime.fromisoformat(expires_raw.replace("Z", "+00:00"))
        logger.info(
            "Refreshed GitHub App installation token (app=%s installation=%s expires_at=%s)",
            self.app_id,
            self.installation_id,
            self._token_expires_at.isoformat(),
        )

    # -- httpx.Auth integration ---------------------------------------------------

    async def async_auth_flow(self, request: httpx.Request):
        if self._token_expiring_soon():
            async with self._lock:
                if self._token_expiring_soon():
                    await self._refresh_installation_token()
        request.headers["Authorization"] = f"Bearer {self._token}"
        request.headers["Accept"] = "application/vnd.github+json"
        request.headers["X-GitHub-Api-Version"] = self.api_version
        yield request


# -- Factory --------------------------------------------------------------------


def _load_private_key(config: AppConfig) -> str:
    """Return the PEM contents, from either a path or an inline value."""
    if config.github_app_private_key_path:
        from pathlib import Path

        return Path(config.github_app_private_key_path).read_text()
    # Tolerate single-line env vars by unescaping literal "\n" sequences.
    return (config.github_app_private_key or "").replace("\\n", "\n")


def build_github_auth(config: AppConfig) -> httpx.Auth:
    """Build the appropriate httpx.Auth handler based on config.

    Prefers GitHub App auth when all App fields are present, otherwise falls
    back to the PAT. Config validation guarantees at least one is set.
    """
    if config.auth_mode == "app":
        assert config.github_app_id is not None
        assert config.github_app_installation_id is not None
        return GitHubAppAuth(
            app_id=config.github_app_id,
            installation_id=config.github_app_installation_id,
            private_key_pem=_load_private_key(config),
            api_version=config.github_api_version,
        )
    return GitHubAuth(config.github_token, config.github_api_version)


# -- Verification ---------------------------------------------------------------


async def verify_token(client: httpx.AsyncClient) -> dict:
    """Verify credentials and return a small info dict.

    Works for both PAT and GitHub App installation tokens. PATs can call
    ``/user``; installation tokens cannot (they 403) but can call
    ``/installation/repositories``. We try ``/user`` first and fall back.
    """
    resp = await client.get("/user")
    if resp.status_code == 200:
        scopes = resp.headers.get("X-OAuth-Scopes", "")
        user = resp.json()
        logger.info("Authenticated as %s (scopes: %s)", user.get("login"), scopes)
        return {
            "mode": "pat",
            "login": user.get("login"),
            "scopes": scopes,
        }

    # Installation token path: /user returns 403. Try /installation/repositories.
    if resp.status_code in (401, 403):
        inst_resp = await client.get("/installation/repositories", params={"per_page": 1})
        if inst_resp.status_code == 200:
            data = inst_resp.json()
            total = data.get("total_count", 0)
            logger.info("Authenticated as GitHub App installation (repos=%d)", total)
            return {
                "mode": "app",
                "login": "github-app-installation",
                "scopes": f"installation ({total} repos accessible)",
            }

    resp.raise_for_status()
    return {"mode": "unknown", "login": "", "scopes": ""}
