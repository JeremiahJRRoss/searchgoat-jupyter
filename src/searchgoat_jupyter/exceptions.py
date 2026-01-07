"""Exception hierarchy for searchgoat."""


class SearchGoatError(Exception):
    """Base exception for all searchgoat errors."""
    pass


class AuthenticationError(SearchGoatError):
    """
    OAuth2 authentication failed.
    
    Common causes:
    - Invalid CRIBL_CLIENT_ID or CRIBL_CLIENT_SECRET
    - Expired credentials
    - Network connectivity to login.cribl.cloud
    """
    pass


class QuerySyntaxError(SearchGoatError):
    """
    Cribl Search rejected the query syntax.
    
    The query must start with 'cribl dataset="..."'.
    Test your query in the Cribl Search UI first.
    """
    pass


class JobTimeoutError(SearchGoatError):
    """
    Search job did not complete within the timeout period.
    
    Consider:
    - Narrowing the time range (earliest/latest)
    - Adding filters to reduce data volume
    - Increasing the timeout parameter
    """
    pass


class JobFailedError(SearchGoatError):
    """
    Search job failed on the Cribl server.
    
    Check the Cribl Search logs for details.
    The job_id and error message are available on this exception.
    """
    
    def __init__(self, message: str, job_id: str | None = None):
        super().__init__(message)
        self.job_id = job_id


class RateLimitError(SearchGoatError):
    """
    API rate limit exceeded (HTTP 429).
    
    The retry_after attribute indicates how many seconds to wait.
    """
    
    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after
