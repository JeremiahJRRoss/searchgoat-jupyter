"""Pagination utilities for Cribl Search results."""

import json
from typing import AsyncIterator

import httpx


async def paginate_results(
    client: httpx.AsyncClient,
    url: str,
    headers: dict,
    page_size: int = 1000,
) -> AsyncIterator[dict]:
    """
    Async generator that handles offset/limit pagination.
    
    Cribl returns NDJSON where the first line is metadata and
    subsequent lines are event records.
    
    Args:
        client: Authenticated httpx.AsyncClient
        url: Results endpoint URL (without query params)
        headers: Request headers including Authorization
        page_size: Records per request (default: 1000)
        
    Yields:
        Individual event dictionaries
        
    Example:
        async for record in paginate_results(client, url, headers):
            print(record["_raw"])
    """
    offset = 0
    total_count: int | None = None
    
    while True:
        params = {"limit": page_size, "offset": offset}
        response = await client.get(
            url,
            params=params,
            headers={**headers, "Accept": "application/x-ndjson"},
        )
        response.raise_for_status()
        
        lines = response.text.strip().split("\n")
        if not lines:
            break
        
        # First line is metadata
        metadata = json.loads(lines[0])
        total_count = metadata.get("totalEventCount", 0)
        
        # Remaining lines are events
        for line in lines[1:]:
            if line.strip():
                yield json.loads(line)
        
        # Check if we've retrieved all records
        offset += page_size
        if total_count is None or offset >= total_count:
            break
