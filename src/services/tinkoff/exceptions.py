"""
Custom exceptions for Tinkoff API client.
"""

from typing import Optional


class TinkoffAPIError(Exception):
    """Base exception for Tinkoff API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class TinkoffNetworkError(TinkoffAPIError):
    """Raised when there are network-related issues."""
    pass


class TinkoffTimeoutError(TinkoffAPIError):
    """Raised when a request times out."""
    pass


class TinkoffRateLimitError(TinkoffAPIError):
    """Raised when rate limit is exceeded."""
    pass


class TinkoffAuthError(TinkoffAPIError):
    """Raised when there are authentication issues."""
    pass


class TinkoffValidationError(TinkoffAPIError):
    """Raised when request validation fails."""
    pass 