"""Base HTTP client for GitHub API with retry, rate limiting, and error handling."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from .auth import GitHubAuth

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0


class GitHubAPIError(Exception):
    """Raised when a GitHub API call fails with a meaningful error."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"GitHub API {status_code}: {message}")


class GitHubBaseClient:
    """Async HTTP client for GitHub API with retry and rate-limit handling.

    Args:
        auth: An ``httpx.Auth`` instance (``GitHubAuth`` for PAT, or
            ``GitHubAppAuth`` for GitHub App installation auth). For backwards
            compatibility, a raw token string is also accepted.
        api_version: GitHub API version header (used only when a raw token is
            passed).
    """

    def __init__(
        self,
        auth: httpx.Auth | str,
        api_version: str = "2026-03-10",
    ) -> None:
        if isinstance(auth, str):
            auth = GitHubAuth(auth, api_version)
        self._auth = auth
        self._client = httpx.AsyncClient(
            base_url=GITHUB_API_BASE,
            auth=self._auth,
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> GitHubBaseClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Make an API request with retry and rate-limit handling.

        Args:
            method: HTTP method (GET, POST, etc.).
            path: API path (e.g., /orgs/{org}/copilot/metrics).
            params: Query parameters.
            json_body: JSON request body.

        Returns:
            httpx.Response object.

        Raises:
            GitHubAPIError: On non-retryable errors.
        """
        last_exc: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = await self._client.request(
                    method, path, params=params, json=json_body
                )

                # Rate limit handling
                remaining = resp.headers.get("X-RateLimit-Remaining")
                if remaining is not None and int(remaining) < 10:
                    reset_at = int(resp.headers.get("X-RateLimit-Reset", "0"))
                    logger.warning(
                        "Rate limit low: %s remaining, resets at %s",
                        remaining,
                        reset_at,
                    )

                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", "60"))
                    logger.warning(
                        "Rate limited, waiting %ds (attempt %d/%d)",
                        retry_after,
                        attempt,
                        MAX_RETRIES,
                    )
                    await asyncio.sleep(retry_after)
                    continue

                if resp.status_code == 403:
                    body = resp.json() if resp.content else {}
                    msg = body.get("message", "Forbidden")
                    raise GitHubAPIError(403, f"Insufficient permissions: {msg}")

                if resp.status_code == 422:
                    body = resp.json() if resp.content else {}
                    msg = body.get("message", "Unprocessable Entity")
                    raise GitHubAPIError(
                        422,
                        f"Copilot metrics may be disabled or unavailable: {msg}",
                    )

                if resp.status_code >= 500:
                    logger.warning(
                        "Server error %d (attempt %d/%d)",
                        resp.status_code,
                        attempt,
                        MAX_RETRIES,
                    )
                    last_exc = GitHubAPIError(resp.status_code, resp.text)
                    await asyncio.sleep(INITIAL_BACKOFF * (2 ** (attempt - 1)))
                    continue

                resp.raise_for_status()
                return resp

            except httpx.TransportError as exc:
                logger.warning(
                    "Transport error: %s (attempt %d/%d)",
                    exc,
                    attempt,
                    MAX_RETRIES,
                )
                last_exc = exc
                await asyncio.sleep(INITIAL_BACKOFF * (2 ** (attempt - 1)))

        raise GitHubAPIError(0, f"Request failed after {MAX_RETRIES} retries: {last_exc}")

    async def get(self, path: str, **kwargs: Any) -> httpx.Response:
        """Shorthand for GET requests."""
        return await self.request("GET", path, **kwargs)

    async def download_ndjson(self, url: str) -> list[dict[str, Any]]:
        """Download and parse an NDJSON file from a signed URL.

        Args:
            url: Signed download URL (full URL, not a path).

        Returns:
            List of parsed JSON objects (one per line).
        """
        import json

        # Use a separate client without auth for signed URLs
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0), follow_redirects=True) as dl:
            resp = await dl.get(url)
            resp.raise_for_status()

        records: list[dict[str, Any]] = []
        for line in resp.text.strip().splitlines():
            line = line.strip()
            if line:
                records.append(json.loads(line))
        return records
