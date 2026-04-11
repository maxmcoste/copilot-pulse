"""Tests for GitHub authentication helpers (PAT + GitHub App)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from src.github_client.auth import (
    GitHubAppAuth,
    GitHubAuth,
    build_github_auth,
)
from src.github_client.base_client import GitHubBaseClient


@pytest.fixture(scope="module")
def rsa_keypair() -> tuple[str, str]:
    """Generate an ephemeral RSA keypair for signing test JWTs."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


class TestGitHubAppAuth:
    def test_generate_jwt_is_valid_rs256(self, rsa_keypair: tuple[str, str]) -> None:
        private_pem, public_pem = rsa_keypair
        auth = GitHubAppAuth(app_id=12345, installation_id=67890, private_key_pem=private_pem)

        token = auth._generate_jwt()
        decoded = jwt.decode(token, public_pem, algorithms=["RS256"])

        assert decoded["iss"] == "12345"
        assert decoded["exp"] > decoded["iat"]
        # Backdated by 60s for clock skew.
        now = int(datetime.now(tz=timezone.utc).timestamp())
        assert decoded["iat"] <= now

    def test_token_expiring_soon_when_unset(self, rsa_keypair: tuple[str, str]) -> None:
        private_pem, _ = rsa_keypair
        auth = GitHubAppAuth(1, 2, private_pem)
        assert auth._token_expiring_soon() is True

        auth._token = "abc"
        auth._token_expires_at = datetime.now(tz=timezone.utc) + timedelta(hours=1)
        assert auth._token_expiring_soon() is False

        auth._token_expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=10)
        assert auth._token_expiring_soon() is True

    @pytest.mark.asyncio
    async def test_refresh_and_use_installation_token(
        self, rsa_keypair: tuple[str, str], httpx_mock
    ) -> None:
        private_pem, _ = rsa_keypair
        expires = (datetime.now(tz=timezone.utc) + timedelta(hours=1)).isoformat()
        # Match the installation-token exchange.
        httpx_mock.add_response(
            method="POST",
            url="https://api.github.com/app/installations/67890/access_tokens",
            json={"token": "ghs_installationtoken", "expires_at": expires.replace("+00:00", "Z")},
        )
        # Match the downstream API call that uses the installation token.
        httpx_mock.add_response(
            method="GET",
            url="https://api.github.com/orgs/acme/copilot/metrics/reports/organization-28-day/latest",
            json={"ok": True},
        )

        auth = GitHubAppAuth(app_id=12345, installation_id=67890, private_key_pem=private_pem)
        client = GitHubBaseClient(auth)
        try:
            resp = await client.get(
                "/orgs/acme/copilot/metrics/reports/organization-28-day/latest"
            )
            assert resp.status_code == 200
            assert resp.json() == {"ok": True}
        finally:
            await client.close()

        # Verify the downstream request carried the installation token, not the JWT.
        requests = httpx_mock.get_requests()
        api_req = [r for r in requests if "/orgs/acme/" in str(r.url)][0]
        assert api_req.headers["Authorization"] == "Bearer ghs_installationtoken"

        # And that a second call reuses the cached token (no extra refresh).
        httpx_mock.add_response(
            method="GET",
            url="https://api.github.com/orgs/acme/copilot/metrics/reports/organization-28-day/latest",
            json={"ok": True},
        )
        client2 = GitHubBaseClient(auth)
        try:
            await client2.get(
                "/orgs/acme/copilot/metrics/reports/organization-28-day/latest"
            )
        finally:
            await client2.close()

        refresh_calls = [
            r for r in httpx_mock.get_requests() if r.url.path.endswith("/access_tokens")
        ]
        assert len(refresh_calls) == 1  # still just the one refresh


class TestAuthFactory:
    def test_build_pat_auth(self) -> None:
        from src.config import AppConfig

        cfg = AppConfig(github_token="ghp_realtoken", anthropic_api_key="sk-ant-real")
        auth = build_github_auth(cfg)
        assert isinstance(auth, GitHubAuth)
        assert auth.token == "ghp_realtoken"

    def test_build_app_auth_prefers_app(self, rsa_keypair: tuple[str, str]) -> None:
        from src.config import AppConfig

        private_pem, _ = rsa_keypair
        cfg = AppConfig(
            github_token="ghp_realtoken",
            github_app_id=123,
            github_app_installation_id=456,
            github_app_private_key=private_pem,
            anthropic_api_key="sk-ant-real",
        )
        assert cfg.auth_mode == "app"
        auth = build_github_auth(cfg)
        assert isinstance(auth, GitHubAppAuth)
        assert auth.app_id == 123
        assert auth.installation_id == 456

    def test_missing_all_auth_raises(self) -> None:
        from src.config import AppConfig

        with pytest.raises(ValueError, match="No GitHub authentication"):
            AppConfig(github_token="", anthropic_api_key="sk-ant-real")
