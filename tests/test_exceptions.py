"""Tests for searchgoat.exceptions module."""

import pytest

from searchgoat_jupyter.exceptions import (
    SearchGoatError,
    AuthenticationError,
    QuerySyntaxError,
    JobTimeoutError,
    JobFailedError,
    RateLimitError,
)


class TestExceptionHierarchy:
    """Tests for exception inheritance and attributes."""
    
    def test_all_exceptions_inherit_from_searchgoat_error(self):
        """All custom exceptions inherit from SearchGoatError."""
        exceptions = [
            AuthenticationError,
            QuerySyntaxError,
            JobTimeoutError,
            JobFailedError,
            RateLimitError,
        ]
        for exc_class in exceptions:
            assert issubclass(exc_class, SearchGoatError)
    
    def test_searchgoat_error_inherits_from_exception(self):
        """SearchGoatError inherits from base Exception."""
        assert issubclass(SearchGoatError, Exception)
    
    def test_exceptions_can_be_raised_and_caught(self):
        """All exceptions can be raised and caught."""
        with pytest.raises(AuthenticationError):
            raise AuthenticationError("auth failed")
        
        with pytest.raises(QuerySyntaxError):
            raise QuerySyntaxError("bad query")
        
        with pytest.raises(JobTimeoutError):
            raise JobTimeoutError("timeout")
    
    def test_catching_base_catches_all(self):
        """Catching SearchGoatError catches all derived exceptions."""
        with pytest.raises(SearchGoatError):
            raise AuthenticationError("auth failed")
        
        with pytest.raises(SearchGoatError):
            raise RateLimitError("rate limited")


class TestJobFailedError:
    """Tests for JobFailedError attributes."""
    
    def test_stores_job_id(self):
        """JobFailedError stores the job_id attribute."""
        exc = JobFailedError("Job failed", job_id="job-123")
        assert exc.job_id == "job-123"
        assert str(exc) == "Job failed"
    
    def test_job_id_defaults_to_none(self):
        """job_id defaults to None if not provided."""
        exc = JobFailedError("Job failed")
        assert exc.job_id is None


class TestRateLimitError:
    """Tests for RateLimitError attributes."""
    
    def test_stores_retry_after(self):
        """RateLimitError stores retry_after attribute."""
        exc = RateLimitError("Too many requests", retry_after=120)
        assert exc.retry_after == 120
        assert str(exc) == "Too many requests"
    
    def test_retry_after_defaults_to_60(self):
        """retry_after defaults to 60 seconds."""
        exc = RateLimitError("Too many requests")
        assert exc.retry_after == 60
