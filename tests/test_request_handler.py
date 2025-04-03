import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from src.models.base import Message, Context, AgentResponse
from src.agent.request_handler import RequestHandler
from src.agent.message_handler import MessageHandler


@pytest.fixture
def mock_message_handler():
    """Create mock message handler."""
    handler = Mock(spec=MessageHandler)
    handler.handle_message = AsyncMock()
    return handler


@pytest.fixture
def request_handler(mock_message_handler):
    """Create request handler with mock dependencies."""
    return RequestHandler(mock_message_handler)


@pytest.fixture
def sample_request():
    """Create sample request."""
    return {
        "type": "portfolio_info",
        "content": "Show me my portfolio",
        "parameters": {"period": "1m"},
        "timestamp": datetime.now()
    }


@pytest.mark.asyncio
async def test_handle_request_success(request_handler, mock_message_handler, sample_request):
    """Test successful request handling."""
    # Setup mock response
    mock_response = AgentResponse(
        message=Message(
            content="Portfolio information...",
            role="assistant",
            metadata={"tool_results": [{"status": "success"}]}
        ),
        context=Context(),
        tool_calls=[{"status": "success"}]
    )
    mock_message_handler.handle_message.return_value = mock_response
    
    # Handle request
    response = await request_handler.handle_request(sample_request)
    
    # Verify response
    assert response["type"] == sample_request["type"]
    assert response["content"] == "Portfolio information..."
    assert "timestamp" in response
    assert response["metadata"] == {"tool_results": [{"status": "success"}]}
    assert response["context"] is not None
    
    # Verify message handler was called correctly
    mock_message_handler.handle_message.assert_called_once()
    call_args = mock_message_handler.handle_message.call_args
    message_arg = call_args[0][0]
    assert message_arg.content == sample_request["content"]
    assert message_arg.role == "user"
    assert message_arg.metadata["type"] == sample_request["type"]
    assert message_arg.metadata["parameters"] == sample_request["parameters"]


@pytest.mark.asyncio
async def test_handle_request_with_context(request_handler, mock_message_handler, sample_request):
    """Test request handling with existing context."""
    # Add context to request
    existing_context = {
        "messages": [],
        "tools": [],
        "metadata": {"session_id": "test123"}
    }
    sample_request["context"] = existing_context
    
    # Setup mock response
    mock_response = AgentResponse(
        message=Message(
            content="Portfolio information...",
            role="assistant",
            metadata={"tool_results": [{"status": "success"}]}
        ),
        context=Context(**existing_context),
        tool_calls=[{"status": "success"}]
    )
    mock_message_handler.handle_message.return_value = mock_response
    
    # Handle request
    response = await request_handler.handle_request(sample_request)
    
    # Verify context was passed correctly
    mock_message_handler.handle_message.assert_called_once()
    context_arg = mock_message_handler.handle_message.call_args[0][1]
    assert context_arg.metadata == existing_context["metadata"]


@pytest.mark.asyncio
async def test_handle_request_error(request_handler, mock_message_handler, sample_request):
    """Test request handling with error."""
    # Setup mock to raise exception
    mock_message_handler.handle_message.side_effect = ValueError("Invalid request")
    
    # Handle request
    response = await request_handler.handle_request(sample_request)
    
    # Verify error response
    assert response["type"] == "error"
    assert "Error processing request" in response["content"]
    assert "Invalid request" in response["content"]
    assert response["metadata"]["error"] == "Invalid request"
    assert response["context"] is None


@pytest.mark.asyncio
async def test_handle_request_missing_parameters(request_handler, mock_message_handler):
    """Test request handling with missing optional parameters."""
    # Create request with minimal required fields
    minimal_request = {
        "type": "portfolio_info",
        "content": "Show portfolio"
    }
    
    # Setup mock response
    mock_response = AgentResponse(
        message=Message(
            content="Portfolio information...",
            role="assistant",
            metadata={"tool_results": [{"status": "success"}]}
        ),
        context=Context(),
        tool_calls=[{"status": "success"}]
    )
    mock_message_handler.handle_message.return_value = mock_response
    
    # Handle request
    response = await request_handler.handle_request(minimal_request)
    
    # Verify response
    assert response["type"] == minimal_request["type"]
    assert response["content"] == "Portfolio information..."
    assert "timestamp" in response
    
    # Verify message handler was called with default values
    mock_message_handler.handle_message.assert_called_once()
    message_arg = mock_message_handler.handle_message.call_args[0][0]
    assert message_arg.metadata["parameters"] == {} 