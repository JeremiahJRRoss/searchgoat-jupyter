"""Tests for searchgoat.auth module."""

import time
import pytest
import respx
from httpx import Response, AsyncClient

from searchgoat_jupyter.auth import TokenManager
from searchgoat_jupyter.config import CriblSettings
from searchgoat_jupyter.exceptions import AuthenticationError


@pytest.fixture
def settings():
    """Test settings."""
    return CriblSettings(
        client_id="test-client-id",
        client_secret="test-client-secret",
        org_id="test-org",
        workspace="test-workspace",
    )


@pytest.fixture
def token_manager(settings):
    """TokenManager with test settings."""
    return TokenManager(settings)


class TestTokenManager:
    """Tests for TokenManager OAuth2 handling."""
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_get_token_authenticates_on_first_call(self, token_manager):
        """First call to get_token triggers authentication."""
        respx.post("https://login.cribl.cloud/oauth/token").mock(
            return_value=Response(
                200,
                json={
                    "access_token": "test-token-abc123",
                    "expires_in": 86400,
                    "token_type": "Bearer",
                },
            )
        )
        
        async with AsyncClient() as client:
            token = await token_manager.get_token(client)
        
        assert token == "test-token-abc123"
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_get_token_reuses_valid_token(self, token_manager):
        """Subsequent calls reuse cached token without re-authenticating."""
        auth_route = respx.post("https://login.cribl.cloud/oauth/token").mock(
            return_value=Response(
                200,
                json={"access_token": "cached-token", "expires_in": 86400},
            )
        )
        
        async with AsyncClient() as client:
            token1 = await token_manager.get_token(client)
            token2 = await token_manager.get_token(client)
        
        assert token1 == token2 == "cached-token"
        assert auth_route.call_count == 1  # Only one auth call
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_get_token_refreshes_when_near_expiry(self, token_manager):
        """Token is refreshed when within REFRESH_BUFFER_SECONDS of expiry."""
        respx.post("https://login.cribl.cloud/oauth/token").mock(
            return_value=Response(
                200,
                json={"access_token": "new-token", "expires_in": 86400},
            )
        )
        
        # Manually set token as about to expire
        token_manager._token = "old-token"
        token_manager._expires_at = time.time() + 60  # 60 seconds left (< 300 buffer)
        
        async with AsyncClient() as client:
            token = await token_manager.get_token(client)
        
        assert token == "new-token"  # Got refreshed token
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_authentication_error_on_401(self, token_manager):
        """AuthenticationError raised on 401 response."""
        respx.post("https://login.cribl.cloud/oauth/token").mock(
            return_value=Response(401, json={"error": "invalid_client"})
        )
        
        async with AsyncClient() as client:
            with pytest.raises(AuthenticationError) as exc_info:
                await token_manager.get_token(client)
        
        assert "401" in str(exc_info.value)
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_authentication_error_on_network_failure(self, token_manager):
        """AuthenticationError raised on network failure."""
        import httpx
        respx.post("https://login.cribl.cloud/oauth/token").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        
        async with AsyncClient() as client:
            with pytest.raises(AuthenticationError) as exc_info:
                await token_manager.get_token(client)
        
        assert "failed" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_clear_forces_reauthentication(self, token_manager):
        """clear() forces re-authentication on next get_token call."""
        auth_route = respx.post("https://login.cribl.cloud/oauth/token").mock(
            return_value=Response(
                200,
                json={"access_token": "token", "expires_in": 86400},
            )
        )
        
        async with AsyncClient() as client:
            await token_manager.get_token(client)
            token_manager.clear()
            await token_manager.get_token(client)
        
        assert auth_route.call_count == 2
    
    def test_is_token_valid_false_when_no_token(self, token_manager):
        """_is_token_valid returns False when no token set."""
        assert token_manager._is_token_valid is False
    
    def test_is_token_valid_false_when_expired(self, token_manager):
        """_is_token_valid returns False when token is expired."""
        token_manager._token = "some-token"
        token_manager._expires_at = time.time() - 100  # Expired
        
        assert token_manager._is_token_valid is False
    
    def test_is_token_valid_false_when_near_expiry(self, token_manager):
        """_is_token_valid returns False within REFRESH_BUFFER_SECONDS."""
        token_manager._token = "some-token"
        # 4 minutes left (less than 5 minute buffer)
        token_manager._expires_at = time.time() + 240
        
        assert token_manager._is_token_valid is False
    
    def test_is_token_valid_true_when_fresh(self, token_manager):
        """_is_token_valid returns True when token has plenty of time."""
        token_manager._token = "some-token"
        token_manager._expires_at = time.time() + 3600  # 1 hour left
        
        assert token_manager._is_token_valid is True
