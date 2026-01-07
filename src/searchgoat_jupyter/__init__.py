"""
searchgoat-jupyter - Query Cribl Search from Jupyter notebooks. Get DataFrames.

Quick Start
-----------
    from searchgoat_jupyter import SearchClient

    client = SearchClient()
    df = client.query('cribl dataset="logs" | limit 1000', earliest="-24h")

Configuration
-------------
Set these environment variables (or use a .env file):

    CRIBL_CLIENT_ID      - Your Cribl API client ID
    CRIBL_CLIENT_SECRET  - Your Cribl API client secret
    CRIBL_ORG_ID         - Your Cribl organization ID
    CRIBL_WORKSPACE      - Your Cribl workspace name

Job-Based Workflow
------------------
    job = client.submit('cribl dataset="logs"', earliest="-7d")
    job.wait()
    df = job.to_dataframe()
    job.save("results.parquet")

Exceptions
----------
    AuthenticationError  - Invalid or expired credentials
    QuerySyntaxError     - Malformed Cribl query
    JobTimeoutError      - Search didn't complete in time
    JobFailedError       - Server-side search failure
    RateLimitError       - Too many requests (see retry_after)

Full Documentation
------------------
    https://github.com/hackish-pub/searchgoat-jupyter#readme

Part of the hackish.pub project family.
"""

__version__ = "0.5.0"

# Enable nested asyncio event loops (required for Jupyter notebooks)
import nest_asyncio
nest_asyncio.apply()

from searchgoat_jupyter.client import SearchClient
from searchgoat_jupyter.job import SearchJob
from searchgoat_jupyter.exceptions import (
    SearchGoatError,
    AuthenticationError,
    QuerySyntaxError,
    JobTimeoutError,
    JobFailedError,
    RateLimitError,
)

__all__ = [
    "SearchClient",
    "SearchJob",
    "SearchGoatError",
    "AuthenticationError",
    "QuerySyntaxError",
    "JobTimeoutError",
    "JobFailedError",
    "RateLimitError",
    "__version__",
]
