"""Tests for searchgoat.job module."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from searchgoat_jupyter.job import JobStatus, SearchJob


class TestJobStatus:
    """Tests for JobStatus enum."""
    
    def test_status_values(self):
        """JobStatus has expected values."""
        assert JobStatus.NEW.value == "new"
        assert JobStatus.QUEUED.value == "queued"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.CANCELED.value == "canceled"
    
    def test_status_from_string(self):
        """JobStatus can be created from string."""
        assert JobStatus("completed") == JobStatus.COMPLETED
        assert JobStatus("running") == JobStatus.RUNNING
        assert JobStatus("queued") == JobStatus.QUEUED


class TestSearchJob:
    """Tests for SearchJob dataclass."""
    
    @pytest.fixture
    def mock_client(self):
        """Mock SearchClient."""
        client = MagicMock()
        client._wait_for_job = AsyncMock()
        client._get_results_as_dataframe = AsyncMock(
            return_value=pd.DataFrame({"col": [1, 2, 3]})
        )
        client._stream_results = AsyncMock()
        return client
    
    def test_job_creation(self, mock_client):
        """SearchJob can be created with id and client."""
        job = SearchJob(id="job-123", _client=mock_client)
        
        assert job.id == "job-123"
        assert job.status == JobStatus.NEW
        assert job.record_count is None
    
    def test_job_repr_hides_client(self, mock_client):
        """SearchJob repr doesn't show _client."""
        job = SearchJob(id="job-123", _client=mock_client)
        repr_str = repr(job)
        
        assert "job-123" in repr_str
        assert "_client" not in repr_str
    
    @pytest.mark.asyncio
    async def test_wait_async_delegates_to_client(self, mock_client):
        """wait_async calls client._wait_for_job."""
        job = SearchJob(id="job-123", _client=mock_client)
        
        await job.wait_async(poll_interval=1.0, timeout=60.0)
        
        mock_client._wait_for_job.assert_called_once_with(job, 1.0, 60.0)
    
    @pytest.mark.asyncio
    async def test_to_dataframe_async_returns_dataframe(self, mock_client):
        """to_dataframe_async returns DataFrame from client."""
        job = SearchJob(id="job-123", _client=mock_client)
        
        df = await job.to_dataframe_async()
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        mock_client._get_results_as_dataframe.assert_called_once_with(job)
    
    @pytest.mark.asyncio
    async def test_save_async_parquet(self, mock_client):
        """save_async saves as parquet when extension is .parquet."""
        job = SearchJob(id="job-123", _client=mock_client)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "output.parquet"
            result = await job.save_async(path)
            
            assert result.exists()
            assert result.suffix == ".parquet"
            
            # Verify it's readable
            df = pd.read_parquet(result)
            assert len(df) == 3
    
    @pytest.mark.asyncio
    async def test_save_async_csv(self, mock_client):
        """save_async saves as CSV when extension is .csv."""
        job = SearchJob(id="job-123", _client=mock_client)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "output.csv"
            result = await job.save_async(path)
            
            assert result.exists()
            assert result.suffix == ".csv"
            
            # Verify it's readable
            df = pd.read_csv(result)
            assert len(df) == 3
    
    @pytest.mark.asyncio
    async def test_save_async_invalid_extension(self, mock_client):
        """save_async raises ValueError for unsupported extensions."""
        job = SearchJob(id="job-123", _client=mock_client)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "output.json"
            
            with pytest.raises(ValueError) as exc_info:
                await job.save_async(path)
            
            assert ".json" in str(exc_info.value)
            assert ".parquet" in str(exc_info.value)
            assert ".csv" in str(exc_info.value)
