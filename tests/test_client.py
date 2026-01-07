"""Tests for searchgoat.client module."""

import pytest
import respx
from httpx import Response, AsyncClient

from searchgoat_jupyter.client import SearchClient
from searchgoat_jupyter.config import CriblSettings
from searchgoat_jupyter.job import JobStatus, SearchJob
from searchgoat_jupyter.exceptions import (
    QuerySyntaxError,
    RateLimitError,
    JobTimeoutError,
    JobFailedError,
)


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
def client(settings):
    """SearchClient with test settings."""
    return SearchClient(settings)


@pytest.fixture
def base_url():
    """Base URL for mocked API."""
    return "https://test-workspace-test-org.cribl.cloud/api/v1/m/default_search"


@pytest.fixture
def mock_auth():
    """Mock auth endpoint."""
    respx.post("https://login.cribl.cloud/oauth/token").mock(
        return_value=Response(
            200,
            json={"access_token": "mock-token", "expires_in": 86400},
        )
    )


class TestSearchClientInit:
    """Tests for SearchClient initialization."""
    
    def test_loads_settings_from_env(self, monkeypatch):
        """Client loads settings from environment if not provided."""
        monkeypatch.setenv("CRIBL_CLIENT_ID", "env-id")
        monkeypatch.setenv("CRIBL_CLIENT_SECRET", "env-secret")
        monkeypatch.setenv("CRIBL_ORG_ID", "env-org")
        monkeypatch.setenv("CRIBL_WORKSPACE", "env-workspace")
        
        client = SearchClient()
        
        assert client.settings.client_id == "env-id"
        assert client.settings.org_id == "env-org"
    
    def test_accepts_explicit_settings(self, settings):
        """Client accepts explicit settings."""
        client = SearchClient(settings)
        
        assert client.settings is settings


class TestSearchClientSubmit:
    """Tests for job submission."""
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_submit_async_returns_job(self, client, base_url, mock_auth):
        """submit_async returns a SearchJob with ID."""
        respx.post(f"{base_url}/search/jobs").mock(
            return_value=Response(
                200,
                json={"items": [{"id": "job-abc123"}]},
            )
        )
        
        job = await client.submit_async('cribl dataset="logs"')
        
        assert isinstance(job, SearchJob)
        assert job.id == "job-abc123"
        assert job.status == JobStatus.NEW
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_submit_async_raises_query_syntax_error(self, client, base_url, mock_auth):
        """submit_async raises QuerySyntaxError on 400."""
        respx.post(f"{base_url}/search/jobs").mock(
            return_value=Response(400, text="Invalid query syntax")
        )
        
        with pytest.raises(QuerySyntaxError) as exc_info:
            await client.submit_async("bad query")
        
        assert "Invalid query" in str(exc_info.value)
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_submit_async_raises_rate_limit_error(self, client, base_url, mock_auth):
        """submit_async raises RateLimitError on 429."""
        respx.post(f"{base_url}/search/jobs").mock(
            return_value=Response(429, headers={"Retry-After": "120"})
        )
        
        with pytest.raises(RateLimitError) as exc_info:
            await client.submit_async('cribl dataset="logs"')
        
        assert exc_info.value.retry_after == 120


class TestSearchClientWaitForJob:
    """Tests for job status polling."""
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_wait_for_job_completes(self, client, base_url, mock_auth):
        """_wait_for_job updates job status to completed."""
        respx.get(f"{base_url}/search/jobs/job-123/status").mock(
            return_value=Response(
                200,
                json={"items": [{"status": "completed", "numEvents": 42}]},
            )
        )
        
        job = SearchJob(id="job-123", _client=client)
        await client._wait_for_job(job, poll_interval=0.1, timeout=5.0)
        
        assert job.status == JobStatus.COMPLETED
        assert job.record_count == 42
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_wait_for_job_polls_until_complete(self, client, base_url, mock_auth):
        """_wait_for_job polls multiple times until completed."""
        status_route = respx.get(f"{base_url}/search/jobs/job-123/status")
        status_route.side_effect = [
            Response(200, json={"items": [{"status": "running"}]}),
            Response(200, json={"items": [{"status": "running"}]}),
            Response(200, json={"items": [{"status": "completed", "numEvents": 10}]}),
        ]
        
        job = SearchJob(id="job-123", _client=client)
        await client._wait_for_job(job, poll_interval=0.01, timeout=5.0)
        
        assert job.status == JobStatus.COMPLETED
        assert status_route.call_count == 3
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_wait_for_job_raises_timeout(self, client, base_url, mock_auth):
        """_wait_for_job raises JobTimeoutError on timeout."""
        respx.get(f"{base_url}/search/jobs/job-123/status").mock(
            return_value=Response(200, json={"items": [{"status": "running"}]})
        )
        
        job = SearchJob(id="job-123", _client=client)
        
        with pytest.raises(JobTimeoutError) as exc_info:
            await client._wait_for_job(job, poll_interval=0.01, timeout=0.05)
        
        assert "job-123" in str(exc_info.value)
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_wait_for_job_raises_failed(self, client, base_url, mock_auth):
        """_wait_for_job raises JobFailedError on failed status."""
        respx.get(f"{base_url}/search/jobs/job-123/status").mock(
            return_value=Response(
                200,
                json={"items": [{"status": "failed", "error": "Dataset not found"}]},
            )
        )
        
        job = SearchJob(id="job-123", _client=client)
        
        with pytest.raises(JobFailedError) as exc_info:
            await client._wait_for_job(job, poll_interval=0.1, timeout=5.0)
        
        assert "Dataset not found" in str(exc_info.value)
        assert exc_info.value.job_id == "job-123"
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_wait_for_job_raises_on_canceled(self, client, base_url, mock_auth):
        """_wait_for_job raises JobFailedError on canceled status."""
        respx.get(f"{base_url}/search/jobs/job-123/status").mock(
            return_value=Response(200, json={"items": [{"status": "canceled"}]})
        )
        
        job = SearchJob(id="job-123", _client=client)
        
        with pytest.raises(JobFailedError) as exc_info:
            await client._wait_for_job(job, poll_interval=0.1, timeout=5.0)
        
        assert "canceled" in str(exc_info.value).lower()


class TestSearchClientResults:
    """Tests for result retrieval."""
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_get_results_as_dataframe(self, client, base_url, mock_auth):
        """_get_results_as_dataframe returns pandas DataFrame."""
        ndjson = (
            '{"isFinished":true,"totalEventCount":2,"offset":0}\n'
            '{"_time":1704067200,"message":"log1"}\n'
            '{"_time":1704067201,"message":"log2"}\n'
        )
        respx.get(f"{base_url}/search/jobs/job-123/results").mock(
            return_value=Response(200, text=ndjson)
        )
        
        job = SearchJob(id="job-123", _client=client)
        df = await client._get_results_as_dataframe(job)
        
        assert len(df) == 2
        assert "message" in df.columns
        assert df["message"].tolist() == ["log1", "log2"]
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_stream_by_id_yields_records(self, client, base_url, mock_auth):
        """_stream_by_id yields individual records."""
        ndjson = (
            '{"isFinished":true,"totalEventCount":2,"offset":0}\n'
            '{"id":1}\n'
            '{"id":2}\n'
        )
        respx.get(f"{base_url}/search/jobs/job-123/results").mock(
            return_value=Response(200, text=ndjson)
        )
        
        records = []
        async for record in client._stream_by_id("job-123"):
            records.append(record)
        
        assert len(records) == 2
        assert records[0]["id"] == 1
        assert records[1]["id"] == 2


class TestSearchClientQuery:
    """Tests for the high-level query method."""
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_query_async_end_to_end(self, client, base_url, mock_auth):
        """query_async handles full workflow."""
        # Submit returns job
        respx.post(f"{base_url}/search/jobs").mock(
            return_value=Response(200, json={"items": [{"id": "job-e2e"}]})
        )
        
        # Status returns completed
        respx.get(f"{base_url}/search/jobs/job-e2e/status").mock(
            return_value=Response(
                200,
                json={"items": [{"status": "completed", "numEvents": 1}]},
            )
        )
        
        # Results
        ndjson = (
            '{"isFinished":true,"totalEventCount":1,"offset":0}\n'
            '{"data":"test"}\n'
        )
        respx.get(f"{base_url}/search/jobs/job-e2e/results").mock(
            return_value=Response(200, text=ndjson)
        )
        
        df = await client.query_async('cribl dataset="test"', earliest="-1h")
        
        assert len(df) == 1
        assert df["data"].iloc[0] == "test"
