"""Shared pytest fixtures for searchgoat tests."""

import pytest
import respx
from httpx import Response

from searchgoat_jupyter.config import CriblSettings


@pytest.fixture
def mock_settings():
    """Return test settings that don't require real credentials."""
    return CriblSettings(
        client_id="test-client-id",
        client_secret="test-client-secret",
        org_id="test-org",
        workspace="test-workspace",
    )


@pytest.fixture
def mock_auth():
    """Mock the OAuth2 authentication endpoint."""
    with respx.mock:
        respx.post("https://login.cribl.cloud/oauth/token").mock(
            return_value=Response(
                200,
                json={
                    "access_token": "mock-token-12345",
                    "expires_in": 86400,
                    "token_type": "Bearer",
                },
            )
        )
        yield


@pytest.fixture
def mock_api(mock_auth):
    """Mock both auth and API endpoints."""
    base_url = "https://test-workspace-test-org.cribl.cloud/api/v1/m/default_search"
    
    with respx.mock:
        # Auth
        respx.post("https://login.cribl.cloud/oauth/token").mock(
            return_value=Response(
                200,
                json={"access_token": "mock-token", "expires_in": 86400},
            )
        )
        
        # Submit job
        respx.post(f"{base_url}/search/jobs").mock(
            return_value=Response(
                200,
                json={"items": [{"id": "job-123"}]},
            )
        )
        
        # Job status
        respx.get(f"{base_url}/search/jobs/job-123/status").mock(
            return_value=Response(
                200,
                json={"items": [{"status": "completed", "numEvents": 2}]},
            )
        )
        
        # Results (NDJSON)
        ndjson_response = (
            '{"isFinished":true,"totalEventCount":2,"offset":0}\n'
            '{"_time":1704067200,"message":"log line 1"}\n'
            '{"_time":1704067201,"message":"log line 2"}\n'
        )
        respx.get(f"{base_url}/search/jobs/job-123/results").mock(
            return_value=Response(200, text=ndjson_response),
        )
        
        yield
