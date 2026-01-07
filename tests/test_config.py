"""Tests for searchgoat.config module."""

import os
import pytest
from pydantic import ValidationError

from searchgoat_jupyter.config import CriblSettings


class TestCriblSettings:
    """Tests for CriblSettings configuration."""
    
    def test_loads_from_explicit_values(self):
        """Settings can be created with explicit values."""
        settings = CriblSettings(
            client_id="my-client-id",
            client_secret="my-secret",
            org_id="my-org",
            workspace="my-workspace",
        )
        
        assert settings.client_id == "my-client-id"
        assert settings.client_secret.get_secret_value() == "my-secret"
        assert settings.org_id == "my-org"
        assert settings.workspace == "my-workspace"
    
    def test_api_base_url_construction(self, mock_settings):
        """api_base_url property constructs correct URL."""
        expected = "https://test-workspace-test-org.cribl.cloud/api/v1/m/default_search"
        assert mock_settings.api_base_url == expected
    
    def test_default_auth_url(self, mock_settings):
        """Default auth_url points to Cribl.Cloud."""
        assert mock_settings.auth_url == "https://login.cribl.cloud/oauth/token"
    
    def test_auth_url_can_be_overridden(self):
        """auth_url can be customized for on-prem deployments."""
        settings = CriblSettings(
            client_id="id",
            client_secret="secret",
            org_id="org",
            workspace="ws",
            auth_url="https://custom.example.com/auth",
        )
        assert settings.auth_url == "https://custom.example.com/auth"
    
    def test_secret_is_masked_in_repr(self, mock_settings):
        """client_secret should not appear in string representation."""
        repr_str = repr(mock_settings)
        assert "test-client-secret" not in repr_str
        assert "**********" in repr_str or "SecretStr" in repr_str
    
    def test_missing_required_field_raises_error(self, monkeypatch):
        """Missing required fields raise ValidationError."""
        # Clear any env vars that might interfere
        monkeypatch.delenv("CRIBL_CLIENT_ID", raising=False)
        monkeypatch.delenv("CRIBL_CLIENT_SECRET", raising=False)
        monkeypatch.delenv("CRIBL_ORG_ID", raising=False)
        monkeypatch.delenv("CRIBL_WORKSPACE", raising=False)
        
        with pytest.raises(ValidationError):
            CriblSettings()
    
    def test_loads_from_environment_variables(self, monkeypatch):
        """Settings load from CRIBL_* environment variables."""
        monkeypatch.setenv("CRIBL_CLIENT_ID", "env-client-id")
        monkeypatch.setenv("CRIBL_CLIENT_SECRET", "env-secret")
        monkeypatch.setenv("CRIBL_ORG_ID", "env-org")
        monkeypatch.setenv("CRIBL_WORKSPACE", "env-workspace")
        
        settings = CriblSettings()
        
        assert settings.client_id == "env-client-id"
        assert settings.client_secret.get_secret_value() == "env-secret"
        assert settings.org_id == "env-org"
        assert settings.workspace == "env-workspace"
