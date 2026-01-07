"""SearchJob class representing a Cribl Search job."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, AsyncIterator, Optional

import pandas as pd

if TYPE_CHECKING:
    from searchgoat_jupyter.client import SearchClient


class JobStatus(str, Enum):
    """
    Possible states of a search job.
    
    Attributes:
        NEW: Job accepted, not yet running
        QUEUED: Job is queued waiting for resources
        RUNNING: Search in progress
        COMPLETED: Results ready for retrieval
        FAILED: Search encountered an error
        CANCELED: Search was stopped before completion
    """
    NEW = "new"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class SearchJob:
    """
    Represents a submitted Cribl Search job.
    
    Use this class to track job progress, retrieve results, and save data locally.
    
    Attributes:
        id: Unique job identifier from Cribl
        status: Current job state (new, running, completed, failed, canceled)
        record_count: Number of records returned (populated after completion)
        
    Example:
        job = client.submit('cribl dataset="logs"', earliest="-1h")
        job.wait()
        df = job.to_dataframe()
        job.save("results.parquet")
    """
    
    id: str
    _client: "SearchClient" = field(repr=False)
    status: JobStatus = JobStatus.NEW
    record_count: Optional[int] = None
    
    def wait(self, poll_interval: float = 2.0, timeout: float = 300.0) -> None:
        """
        Block until the job completes or fails.
        
        Args:
            poll_interval: Seconds between status checks (default: 2.0)
            timeout: Maximum seconds to wait (default: 300.0 = 5 minutes)
            
        Raises:
            JobTimeoutError: If timeout is exceeded
            JobFailedError: If the job fails on the server
        """
        asyncio.run(self.wait_async(poll_interval, timeout))
    
    async def wait_async(self, poll_interval: float = 2.0, timeout: float = 300.0) -> None:
        """
        Async version of wait().
        
        Args:
            poll_interval: Seconds between status checks
            timeout: Maximum seconds to wait
            
        Raises:
            JobTimeoutError: If timeout is exceeded
            JobFailedError: If the job fails on the server
        """
        await self._client._wait_for_job(self, poll_interval, timeout)
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        Retrieve all results as a pandas DataFrame.
        
        Handles pagination automatically for large result sets.
        
        Returns:
            DataFrame containing all search results
            
        Raises:
            JobFailedError: If job is not in completed state
        """
        return asyncio.run(self.to_dataframe_async())
    
    async def to_dataframe_async(self) -> pd.DataFrame:
        """Async version of to_dataframe()."""
        return await self._client._get_results_as_dataframe(self)
    
    def save(self, path: str | Path) -> Path:
        """
        Save results to a local file.
        
        File format is determined by extension:
        - .parquet: Apache Parquet (recommended for large datasets)
        - .csv: Comma-separated values
        
        Args:
            path: Destination file path
            
        Returns:
            Resolved Path to the saved file
            
        Raises:
            ValueError: If file extension is not .parquet or .csv
        """
        return asyncio.run(self.save_async(path))
    
    async def save_async(self, path: str | Path) -> Path:
        """Async version of save()."""
        path = Path(path)
        df = await self.to_dataframe_async()
        
        if path.suffix == ".parquet":
            df.to_parquet(path, index=False)
        elif path.suffix == ".csv":
            df.to_csv(path, index=False)
        else:
            raise ValueError(f"Unsupported file extension: {path.suffix}. Use .parquet or .csv")
        
        return path.resolve()
    
    async def stream_async(self) -> AsyncIterator[dict]:
        """
        Stream results one record at a time.
        
        Use this for very large result sets that don't fit in memory.
        
        Yields:
            Individual record dictionaries
        """
        async for record in self._client._stream_results(self):
            yield record
