"""
Tests for Tinkoff API client.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
from aiohttp import ClientResponse, ClientTimeout

from src.services.tinkoff.client import TinkoffClient
from src.services.tinkoff.exceptions import (
    TinkoffAPIError,
    TinkoffAuthError,
    TinkoffNetworkError,
    TinkoffRateLimitError,
    TinkoffTimeoutError,
    TinkoffValidationError,
)


@pytest.fixture
def client():
    """Create test client instance."""
    return TinkoffClient("test_token")


@pytest.mark.asyncio
async def test_create_session():
    """Test session creation with correct headers."""
    client = TinkoffClient("test_token")
    session = await client._create_session()
    
    assert isinstance(session, aiohttp.ClientSession)
    assert session._headers["Authorization"] == "Bearer test_token"
    assert session._headers["Content-Type"] == "application/json"
    assert isinstance(session._timeout, ClientTimeout)
    assert session._timeout.total == client.DEFAULT_TIMEOUT


@pytest.mark.asyncio
async def test_handle_response_success():
    """Test successful response handling."""
    client = TinkoffClient("test_token")
    response = AsyncMock(spec=ClientResponse)
    response.status = 200
    response.json.return_value = {"data": "test"}
    
    result = await client._handle_response(response)
    assert result == {"data": "test"}


@pytest.mark.asyncio
async def test_handle_response_server_error():
    """Test server error handling."""
    client = TinkoffClient("test_token")
    response = AsyncMock(spec=ClientResponse)
    response.status = 500
    response.json.return_value = {"message": "Server error"}
    
    with pytest.raises(TinkoffNetworkError) as exc:
        await client._handle_response(response)
    assert exc.value.status_code == 500
    assert "Server error" in str(exc.value)


@pytest.mark.asyncio
async def test_handle_response_rate_limit():
    """Test rate limit error handling."""
    client = TinkoffClient("test_token")
    response = AsyncMock(spec=ClientResponse)
    response.status = 429
    response.json.return_value = {"message": "Rate limit exceeded"}
    
    with pytest.raises(TinkoffRateLimitError) as exc:
        await client._handle_response(response)
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_handle_response_auth_error():
    """Test authentication error handling."""
    client = TinkoffClient("test_token")
    response = AsyncMock(spec=ClientResponse)
    response.status = 401
    response.json.return_value = {"message": "Authentication failed"}
    
    with pytest.raises(TinkoffAuthError) as exc:
        await client._handle_response(response)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_handle_response_validation_error():
    """Test validation error handling."""
    client = TinkoffClient("test_token")
    response = AsyncMock(spec=ClientResponse)
    response.status = 400
    response.json.return_value = {"message": "Validation error"}
    
    with pytest.raises(TinkoffValidationError) as exc:
        await client._handle_response(response)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_rate_limit():
    """Test rate limiting functionality."""
    client = TinkoffClient("test_token")
    
    # Make maximum allowed requests
    for _ in range(client.RATE_LIMIT):
        await client._check_rate_limit()
    
    # Next request should wait
    start_time = asyncio.get_event_loop().time()
    await client._check_rate_limit()
    elapsed = asyncio.get_event_loop().time() - start_time
    
    assert elapsed >= 1.0  # Should wait at least 1 second


@pytest.mark.asyncio
async def test_request_retry_timeout():
    """Test request retry on timeout."""
    client = TinkoffClient("test_token", max_retries=2)
    
    with patch("aiohttp.ClientSession.request") as mock_request:
        mock_request.side_effect = asyncio.TimeoutError()
        
        with pytest.raises(TinkoffTimeoutError):
            await client._request("GET", "test")
        
        assert mock_request.call_count == 3  # Initial + 2 retries


@pytest.mark.asyncio
async def test_request_retry_network_error():
    """Test request retry on network error."""
    client = TinkoffClient("test_token", max_retries=2)
    
    with patch("aiohttp.ClientSession.request") as mock_request:
        mock_request.side_effect = aiohttp.ClientError()
        
        with pytest.raises(TinkoffNetworkError):
            await client._request("GET", "test")
        
        assert mock_request.call_count == 3  # Initial + 2 retries


@pytest.mark.asyncio
async def test_get_request():
    """Test GET request method."""
    client = TinkoffClient("test_token")
    
    with patch.object(client, "_request") as mock_request:
        mock_request.return_value = {"data": "test"}
        result = await client.get("test", {"param": "value"})
        
        mock_request.assert_called_once_with(
            "GET",
            "test",
            params={"param": "value"},
            use_cache=True,
        )
        assert result == {"data": "test"}


@pytest.mark.asyncio
async def test_post_request():
    """Test POST request method."""
    client = TinkoffClient("test_token")
    
    with patch.object(client, "_request") as mock_request:
        mock_request.return_value = {"data": "test"}
        result = await client.post("test", {"data": "value"})
        
        mock_request.assert_called_once_with(
            "POST",
            "test",
            json={"data": "value"},
            use_cache=False,
        )
        assert result == {"data": "test"}


@pytest.mark.asyncio
async def test_cache_get_request():
    """Test GET request caching."""
    client = TinkoffClient("test_token", cache_ttl=1)
    test_data = {"data": "test"}
    
    # Mock the request to return test data
    with patch.object(client, "_request", autospec=True) as mock_request:
        mock_request.return_value = test_data
        
        # First request should hit the API
        result1 = await client.get("test")
        assert result1 == test_data
        assert mock_request.call_count == 1
        
        # Second request should use cache
        result2 = await client.get("test")
        assert result2 == test_data
        assert mock_request.call_count == 1  # No additional API calls
        
        # Wait for cache to expire
        await asyncio.sleep(1.1)
        
        # Third request should hit the API again
        result3 = await client.get("test")
        assert result3 == test_data
        assert mock_request.call_count == 2


@pytest.mark.asyncio
async def test_cache_post_request():
    """Test POST request no caching by default."""
    client = TinkoffClient("test_token")
    test_data = {"data": "test"}
    
    with patch.object(client, "_request", autospec=True) as mock_request:
        mock_request.return_value = test_data
        
        # First request
        result1 = await client.post("test", test_data)
        assert result1 == test_data
        assert mock_request.call_count == 1
        
        # Second request should also hit the API
        result2 = await client.post("test", test_data)
        assert result2 == test_data
        assert mock_request.call_count == 2  # Both requests hit the API


@pytest.mark.asyncio
async def test_cache_clear():
    """Test cache clearing."""
    client = TinkoffClient("test_token")
    test_data = {"data": "test"}
    
    with patch.object(client, "_request", autospec=True) as mock_request:
        mock_request.return_value = test_data
        
        # First request should hit the API
        await client.get("test")
        assert mock_request.call_count == 1
        
        # Second request should use cache
        await client.get("test")
        assert mock_request.call_count == 1
        
        # Clear cache
        client.clear_cache()
        
        # Third request should hit the API again
        await client.get("test")
        assert mock_request.call_count == 2


def test_cache_stats():
    """Test cache statistics."""
    client = TinkoffClient("test_token")
    
    # Initial stats
    stats = client.get_cache_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["hit_ratio"] == 0.0
    assert stats["size"] == 0


@pytest.mark.asyncio
async def test_cache_key_generation():
    """Test cache key generation with different parameters."""
    client = TinkoffClient("test_token")
    
    # Test different request parameters
    key1 = client._get_cache_key("GET", "test", {"a": 1, "b": 2})
    key2 = client._get_cache_key("GET", "test", {"b": 2, "a": 1})  # Same params, different order
    key3 = client._get_cache_key("POST", "test", json={"x": 1})
    
    assert key1 == key2  # Keys should be the same regardless of param order
    assert key1 != key3  # Different method and params should have different keys 