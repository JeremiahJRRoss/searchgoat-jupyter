"""SearchClient - main entry point for searchgoat."""

from __future__ import annotations

import asyncio
import time
from typing import AsyncIterator, Optional

import httpx
import pandas as pd

from searchgoat_jupyter.auth import TokenManager
from searchgoat_jupyter.config import CriblSettings
from searchgoat_jupyter.exceptions import (
    JobFailedError,
    JobTimeoutError,
    QuerySyntaxError,
    RateLimitError,
)
from searchgoat_jupyter.job import JobStatus, SearchJob
from searchgoat_jupyter.pagination import paginate_results
from searchgoat_jupyter._utils.dataframe import records_to_dataframe


class SearchClient:
    """
    Client for querying Cribl Search.
    
    Reads configuration from environment variables (CRIBL_*) automatically.
    Provides both sync and async interfaces.
    
    Example:
        client = SearchClient()
        df = client.query('cribl dataset="logs" | limit 1000', earliest="-24h")
        
    Async Example:
        async with SearchClient() as client:
            job = await client.submit_async('cribl dataset="logs"')
            await job.wait_async()
            df = await job.to_dataframe_async()
            
    Attributes:
        settings: CriblSettings instance with API configuration
    """
    
    def __init__(self, settings: Optional[CriblSettings] = None):
        """
        Initialize the search client.
        
        Args:
            settings: Optional CriblSettings instance. If not provided,
                     settings are loaded from environment variables.
        """
        self.settings = settings or CriblSettings()
        self._token_manager = TokenManager(self.settings)
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self) -> "SearchClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _get_client(self) -> httpx.AsyncClient:
        """Get or create httpx client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def _get_headers(self) -> dict:
        """Get request headers with valid auth token."""
        token = await self._token_manager.get_token(self._get_client())
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
    
    # -------------------------------------------------------------------------
    # Public API: Sync methods (convenience wrappers)
    # -------------------------------------------------------------------------
    
    def query(
        self,
        query: str,
        earliest: str = "-1h",
        latest: str = "now",
        timeout: float = 300.0,
    ) -> pd.DataFrame:
        """
        Execute a query and return results as a DataFrame.
        
        This is the simplest way to get data from Cribl Search.
        Handles job submission, polling, and result retrieval automatically.
        
        Args:
            query: Cribl Search query (must start with 'cribl dataset="..."')
            earliest: Start of time range (default: "-1h")
            latest: End of time range (default: "now")
            timeout: Maximum seconds to wait for completion (default: 300)
            
        Returns:
            pandas DataFrame with query results
            
        Raises:
            QuerySyntaxError: If query syntax is invalid
            JobTimeoutError: If query doesn't complete within timeout
            JobFailedError: If query fails on server
            
        Example:
            df = client.query('cribl dataset="logs" | limit 1000', earliest="-24h")
            print(df.head())
        """
        return asyncio.run(self.query_async(query, earliest, latest, timeout))
    
    def submit(
        self,
        query: str,
        earliest: str = "-1h",
        latest: str = "now",
    ) -> SearchJob:
        """
        Submit a query and return a SearchJob for tracking.
        
        Use this when you want control over polling and result retrieval.
        
        Args:
            query: Cribl Search query
            earliest: Start of time range
            latest: End of time range
            
        Returns:
            SearchJob instance for tracking progress
            
        Example:
            job = client.submit('cribl dataset="logs"', earliest="-7d")
            job.wait()
            print(f"Found {job.record_count} records")
        """
        return asyncio.run(self.submit_async(query, earliest, latest))
    
    def stream(self, job_id: str) -> list[dict]:
        """
        Retrieve results as a list of records.
        
        For the async streaming version, use job.stream_async().
        
        Args:
            job_id: ID of a completed search job
            
        Returns:
            List of record dictionaries
        """
        async def _collect():
            records = []
            async for record in self._stream_by_id(job_id):
                records.append(record)
            return records
        return asyncio.run(_collect())
    
    # -------------------------------------------------------------------------
    # Public API: Async methods
    # -------------------------------------------------------------------------
    
    async def query_async(
        self,
        query: str,
        earliest: str = "-1h",
        latest: str = "now",
        timeout: float = 300.0,
    ) -> pd.DataFrame:
        """
        Async version of query().
        
        Args:
            query: Cribl Search query
            earliest: Start of time range
            latest: End of time range
            timeout: Maximum seconds to wait
            
        Returns:
            pandas DataFrame with query results
        """
        job = await self.submit_async(query, earliest, latest)
        await self._wait_for_job(job, poll_interval=2.0, timeout=timeout)
        return await self._get_results_as_dataframe(job)
    
    async def submit_async(
        self,
        query: str,
        earliest: str = "-1h",
        latest: str = "now",
    ) -> SearchJob:
        """
        Async version of submit().
        
        Args:
            query: Cribl Search query
            earliest: Start of time range
            latest: End of time range
            
        Returns:
            SearchJob instance
        """
        headers = await self._get_headers()
        payload = {
            "query": query,
            "earliest": earliest,
            "latest": latest,
            "sampleRate": 1,
        }
        
        url = f"{self.settings.api_base_url}/search/jobs"
        client = self._get_client()
        
        response = await client.post(url, json=payload, headers=headers)
        
        if response.status_code == 400:
            raise QuerySyntaxError(f"Invalid query: {response.text}")
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            raise RateLimitError("Rate limit exceeded", retry_after=retry_after)
        
        response.raise_for_status()
        
        data = response.json()
        job_id = data["items"][0]["id"]
        
        return SearchJob(id=job_id, _client=self)
    
    # -------------------------------------------------------------------------
    # Internal methods (used by SearchJob)
    # -------------------------------------------------------------------------
    
    async def _wait_for_job(
        self,
        job: SearchJob,
        poll_interval: float,
        timeout: float,
    ) -> None:
        """
        Poll job status until completion or timeout.
        
        Args:
            job: SearchJob to monitor
            poll_interval: Seconds between status checks
            timeout: Maximum seconds to wait
            
        Raises:
            JobTimeoutError: If timeout exceeded
            JobFailedError: If job fails or is canceled
        """
        start_time = time.time()
        headers = await self._get_headers()
        url = f"{self.settings.api_base_url}/search/jobs/{job.id}/status"
        client = self._get_client()
        
        while True:
            if time.time() - start_time > timeout:
                raise JobTimeoutError(
                    f"Job {job.id} did not complete within {timeout} seconds"
                )
            
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            status_str = data["items"][0]["status"]
            job.status = JobStatus(status_str)
            
            if job.status == JobStatus.COMPLETED:
                job.record_count = data["items"][0].get("numEvents", 0)
                return
            
            if job.status == JobStatus.FAILED:
                error_msg = data["items"][0].get("error", "Unknown error")
                raise JobFailedError(error_msg, job_id=job.id)
            
            if job.status == JobStatus.CANCELED:
                raise JobFailedError("Job was canceled", job_id=job.id)
            
            await asyncio.sleep(poll_interval)
    
    async def _get_results_as_dataframe(self, job: SearchJob) -> pd.DataFrame:
        """
        Retrieve all results and convert to DataFrame.
        
        Args:
            job: Completed SearchJob
            
        Returns:
            pandas DataFrame with all results
        """
        records = []
        async for record in self._stream_results(job):
            records.append(record)
        return records_to_dataframe(records)
    
    async def _stream_results(self, job: SearchJob) -> AsyncIterator[dict]:
        """
        Stream results for a job.
        
        Args:
            job: SearchJob to stream results from
            
        Yields:
            Individual record dictionaries
        """
        async for record in self._stream_by_id(job.id):
            yield record
    
    async def _stream_by_id(self, job_id: str) -> AsyncIterator[dict]:
        """
        Stream results by job ID.
        
        Args:
            job_id: ID of completed job
            
        Yields:
            Individual record dictionaries
        """
        headers = await self._get_headers()
        url = f"{self.settings.api_base_url}/search/jobs/{job_id}/results"
        client = self._get_client()
        
        async for record in paginate_results(client, url, headers):
            yield record
