"""OAuth2 token management for Cribl.Cloud."""

import time
from typing import Optional

import httpx

from searchgoat_jupyter.config import CriblSettings
from searchgoat_jupyter.exceptions import AuthenticationError


class TokenManager:
    """
    Manages OAuth2 access tokens with automatic refresh.
    
    Tokens are refreshed proactively when within 5 minutes of expiry,
    avoiding authentication failures mid-request.
    
    Attributes:
        settings: CriblSettings instance with credentials
        
    Example:
        settings = CriblSettings()
        token_manager = TokenManager(settings)
        
        async with httpx.AsyncClient() as client:
            token = await token_manager.get_token(client)
            # Use token for API requests
    """
    
    REFRESH_BUFFER_SECONDS = 300  # Refresh 5 minutes before expiry
    
    def __init__(self, settings: CriblSettings):
        """
        Initialize the token manager.
        
        Args:
            settings: CriblSettings instance containing OAuth2 credentials
        """
        self.settings = settings
        self._token: Optional[str] = None
        self._expires_at: float = 0
    
    @property
    def _is_token_valid(self) -> bool:
        """Check if current token exists and isn't near expiry."""
        if self._token is None:
            return False
        return time.time() < (self._expires_at - self.REFRESH_BUFFER_SECONDS)
    
    async def get_token(self, client: httpx.AsyncClient) -> str:
        """
        Return a valid access token, refreshing if necessary.
        
        Args:
            client: httpx.AsyncClient instance for making the auth request
            
        Returns:
            Valid Bearer token string
            
        Raises:
            AuthenticationError: If authentication fails
        """
        if not self._is_token_valid:
            await self._authenticate(client)
        return self._token  # type: ignore
    
    async def _authenticate(self, client: httpx.AsyncClient) -> None:
        """
        Perform OAuth2 client_credentials flow.
        
        Raises:
            AuthenticationError: If the auth request fails
        """
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.settings.client_id,
            "client_secret": self.settings.client_secret.get_secret_value(),
            "audience": "https://api.cribl.cloud",
        }
        
        try:
            response = await client.post(
                self.settings.auth_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise AuthenticationError(
                f"Authentication failed: {e.response.status_code} - {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise AuthenticationError(
                f"Authentication request failed: {e}"
            ) from e
        
        data = response.json()
        self._token = data["access_token"]
        self._expires_at = time.time() + data.get("expires_in", 86400)
    
    def clear(self) -> None:
        """Clear cached token, forcing re-authentication on next request."""
        self._token = None
        self._expires_at = 0
