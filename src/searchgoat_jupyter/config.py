"""Configuration management via environment variables."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class CriblSettings(BaseSettings):
    """
    Cribl Search API configuration.
    
    All values are read from environment variables prefixed with CRIBL_.
    A .env file in the current directory is loaded automatically.
    
    Attributes:
        client_id: OAuth2 client ID from Cribl.Cloud
        client_secret: OAuth2 client secret (stored securely)
        org_id: Cribl organization identifier
        workspace: Cribl workspace name
        auth_url: OAuth2 token endpoint (rarely needs changing)
        api_base_url: Base URL pattern for API calls
    
    Example:
        # Set environment variables:
        # CRIBL_CLIENT_ID=your-id
        # CRIBL_CLIENT_SECRET=your-secret
        # CRIBL_ORG_ID=your-org
        # CRIBL_WORKSPACE=your-workspace
        
        settings = CriblSettings()
        print(settings.api_base_url)
    """
    
    client_id: str
    client_secret: SecretStr
    org_id: str
    workspace: str
    auth_url: str = "https://login.cribl.cloud/oauth/token"
    
    model_config = SettingsConfigDict(
        env_prefix="CRIBL_",
        env_file=".env",
        env_file_encoding="utf-8",
    )
    
    @property
    def api_base_url(self) -> str:
        """Construct the API base URL from workspace and org_id."""
        return f"https://{self.workspace}-{self.org_id}.cribl.cloud/api/v1/m/default_search"
