"""GitHub authentication helpers."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class GitHubAuth(httpx.Auth):
    """httpx Auth handler for GitHub API token authentication.

    Args:
        token: GitHub personal access token or fine-grained token.
        api_version: GitHub API version header value.
    """

    def __init__(self, token: str, api_version: str = "2026-03-10") -> None:
        self.token = token
        self.api_version = api_version

    def auth_flow(self, request: httpx.Request):
        request.headers["Authorization"] = f"Bearer {self.token}"
        request.headers["Accept"] = "application/vnd.github+json"
        request.headers["X-GitHub-Api-Version"] = self.api_version
        yield request


async def verify_token(client: httpx.AsyncClient) -> dict:
    """Verify the token is valid and return the authenticated user info.

    Returns:
        Dict with user info including login, scopes, etc.

    Raises:
        httpx.HTTPStatusError: If authentication fails.
    """
    resp = await client.get("/user")
    resp.raise_for_status()
    scopes = resp.headers.get("X-OAuth-Scopes", "")
    user = resp.json()
    logger.info("Authenticated as %s (scopes: %s)", user.get("login"), scopes)
    return {"login": user.get("login"), "scopes": scopes}
