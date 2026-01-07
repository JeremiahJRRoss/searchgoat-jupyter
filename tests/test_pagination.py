"""Tests for searchgoat.pagination module."""

import pytest
import respx
from httpx import Response, AsyncClient

from searchgoat_jupyter.pagination import paginate_results


class TestPaginateResults:
    """Tests for paginate_results async generator."""
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_yields_records_from_single_page(self):
        """Yields all records when results fit in one page."""
        ndjson = (
            '{"isFinished":true,"totalEventCount":2,"offset":0}\n'
            '{"id":1,"msg":"first"}\n'
            '{"id":2,"msg":"second"}\n'
        )
        respx.get("https://api.example.com/results").mock(
            return_value=Response(200, text=ndjson)
        )
        
        records = []
        async with AsyncClient() as client:
            async for record in paginate_results(
                client,
                "https://api.example.com/results",
                headers={"Authorization": "Bearer token"},
                page_size=100,
            ):
                records.append(record)
        
        assert len(records) == 2
        assert records[0]["id"] == 1
        assert records[1]["msg"] == "second"
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_paginates_across_multiple_pages(self):
        """Fetches multiple pages when results exceed page_size."""
        page1 = (
            '{"isFinished":false,"totalEventCount":3,"offset":0}\n'
            '{"id":1}\n'
            '{"id":2}\n'
        )
        page2 = (
            '{"isFinished":true,"totalEventCount":3,"offset":2}\n'
            '{"id":3}\n'
        )
        
        route = respx.get("https://api.example.com/results")
        route.side_effect = [
            Response(200, text=page1),
            Response(200, text=page2),
        ]
        
        records = []
        async with AsyncClient() as client:
            async for record in paginate_results(
                client,
                "https://api.example.com/results",
                headers={},
                page_size=2,
            ):
                records.append(record)
        
        assert len(records) == 3
        assert [r["id"] for r in records] == [1, 2, 3]
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_handles_empty_results(self):
        """Handles case with no results gracefully."""
        ndjson = '{"isFinished":true,"totalEventCount":0,"offset":0}\n'
        respx.get("https://api.example.com/results").mock(
            return_value=Response(200, text=ndjson)
        )
        
        records = []
        async with AsyncClient() as client:
            async for record in paginate_results(
                client,
                "https://api.example.com/results",
                headers={},
            ):
                records.append(record)
        
        assert len(records) == 0
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_skips_blank_lines(self):
        """Skips blank lines in NDJSON response."""
        ndjson = (
            '{"isFinished":true,"totalEventCount":2,"offset":0}\n'
            '\n'
            '{"id":1}\n'
            '\n'
            '{"id":2}\n'
            '\n'
        )
        respx.get("https://api.example.com/results").mock(
            return_value=Response(200, text=ndjson)
        )
        
        records = []
        async with AsyncClient() as client:
            async for record in paginate_results(
                client,
                "https://api.example.com/results",
                headers={},
            ):
                records.append(record)
        
        assert len(records) == 2
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_includes_ndjson_accept_header(self):
        """Request includes Accept: application/x-ndjson header."""
        ndjson = '{"isFinished":true,"totalEventCount":0,"offset":0}\n'
        route = respx.get("https://api.example.com/results").mock(
            return_value=Response(200, text=ndjson)
        )
        
        async with AsyncClient() as client:
            async for _ in paginate_results(
                client,
                "https://api.example.com/results",
                headers={"Authorization": "Bearer x"},
            ):
                pass
        
        request = route.calls[0].request
        assert request.headers["Accept"] == "application/x-ndjson"
        assert request.headers["Authorization"] == "Bearer x"
