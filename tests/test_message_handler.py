import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.models.base import Message, Context, AgentResponse
from src.services.tinkoff.portfolio import PortfolioService
from src.agent.message_handler import MessageHandler


@pytest.fixture
def mock_portfolio_service():
    """Create mock portfolio service."""
    return Mock(spec=PortfolioService)


@pytest.fixture
def message_handler(mock_portfolio_service):
    """Create message handler with mock dependencies."""
    return MessageHandler(mock_portfolio_service)


@pytest.fixture
def sample_message():
    """Create sample message."""
    return Message(
        content="Show me my portfolio",
        role="user",
        metadata={"type": "portfolio_info"}
    )


@pytest.fixture
def sample_context():
    """Create sample context."""
    return Context()


@pytest.mark.asyncio
async def test_handle_message_success(message_handler, sample_message, sample_context):
    """Test successful message handling."""
    # Mock analyzer to return tool names
    with patch.object(message_handler.analyzer, "analyze_message") as mock_analyze:
        mock_analyze.return_value = ["portfolio_info"]
        
        # Mock executor to return success result
        mock_result = {
            "account_id": "test_account",
            "total_value": 100000.0,
            "positions": [
                {"ticker": "AAPL", "quantity": 10}
            ],
            "last_update": datetime.now().isoformat()
        }
        with patch.object(message_handler.executor, "execute") as mock_execute:
            mock_execute.return_value = mock_result
            
            # Handle message
            response = await message_handler.handle_message(sample_message, sample_context)
            
            # Verify response
            assert isinstance(response, AgentResponse)
            assert response.message.role == "assistant"
            assert "Portfolio Information" in response.message.content
            assert response.context.messages == [sample_message, response.message]
            assert len(response.tool_calls) == 1
            assert response.tool_calls[0]["status"] == "success"


@pytest.mark.asyncio
async def test_handle_message_tool_error(message_handler, sample_message, sample_context):
    """Test message handling with tool execution error."""
    # Mock analyzer to return tool names
    with patch.object(message_handler.analyzer, "analyze_message") as mock_analyze:
        mock_analyze.return_value = ["portfolio_info"]
        
        # Mock executor to raise exception
        with patch.object(message_handler.executor, "execute") as mock_execute:
            mock_execute.side_effect = ValueError("API Error")
            
            # Handle message
            response = await message_handler.handle_message(sample_message, sample_context)
            
            # Verify error response
            assert isinstance(response, AgentResponse)
            assert response.message.role == "assistant"
            assert "errors" in response.message.content.lower()
            assert "portfolio_info" in response.message.content
            assert response.tool_calls[0]["status"] == "error"
            assert "API Error" in response.tool_calls[0]["error"]


@pytest.mark.asyncio
async def test_handle_message_analyzer_error(message_handler, sample_message, sample_context):
    """Test message handling with analyzer error."""
    # Mock analyzer to raise exception
    with patch.object(message_handler.analyzer, "analyze_message") as mock_analyze:
        mock_analyze.side_effect = ValueError("Analysis Error")
        
        # Handle message
        response = await message_handler.handle_message(sample_message, sample_context)
        
        # Verify error response
        assert isinstance(response, AgentResponse)
        assert response.message.role == "assistant"
        assert "error" in response.message.content.lower()
        assert "Analysis Error" in response.message.metadata["error"]


@pytest.mark.asyncio
async def test_handle_message_multiple_tools(message_handler, sample_message, sample_context):
    """Test handling message requiring multiple tools."""
    # Mock analyzer to return multiple tool names
    with patch.object(message_handler.analyzer, "analyze_message", return_value=["portfolio_info", "portfolio_performance"]) as mock_analyze:
        # Mock executor to return different results for each tool
        mock_results = {
            "portfolio_info": {
                "account_id": "test_account",
                "total_value": 100000.0,
                "positions": [{"ticker": "AAPL", "quantity": 10}],
                "last_update": datetime.now().isoformat()
            },
            "portfolio_performance": {
                "account_id": "test_account",
                "period": "1m",
                "currency": "USD",
                "metrics": {
                    "absolute_return": {"value": 5000, "currency": "USD"},
                    "relative_return": 5.0,
                    "annualized_return": 60.0
                }
            }
        }
        
        async def mock_execute(tool_name, **kwargs):
            return mock_results[tool_name]
        
        with patch.object(message_handler.executor, "execute", side_effect=mock_execute):
            # Handle message
            response = await message_handler.handle_message(sample_message, sample_context)
            
            # Verify response contains both tool results
            assert isinstance(response, AgentResponse)
            assert len(response.tool_calls) == 2
            assert all(call["status"] == "success" for call in response.tool_calls)
            assert "Portfolio Information" in response.message.content
            assert "Portfolio Performance" in response.message.content


def test_format_portfolio_info(message_handler):
    """Test formatting portfolio info result."""
    result = {
        "account_id": "test_account",
        "total_value": 100000.0,
        "positions": [{"ticker": "AAPL", "quantity": 10}],
        "last_update": "2024-04-02T12:00:00"
    }
    
    formatted = message_handler._format_portfolio_info(result)
    assert "Portfolio Information" in formatted
    assert "Account: test_account" in formatted
    assert "Total Value: 100000.0" in formatted
    assert "Positions: 1" in formatted


def test_format_portfolio_performance(message_handler):
    """Test formatting portfolio performance result."""
    result = {
        "account_id": "test_account",
        "period": "1m",
        "currency": "USD",
        "metrics": {
            "absolute_return": {"value": 5000, "currency": "USD"},
            "relative_return": 5.0,
            "annualized_return": 60.0
        }
    }
    
    formatted = message_handler._format_portfolio_performance(result)
    assert "Portfolio Performance (1m)" in formatted
    assert "Account: test_account" in formatted
    assert "Currency: USD" in formatted
    assert "Absolute Return: 5000 USD" in formatted
    assert "Relative Return: 5.0%" in formatted
    assert "Annualized Return: 60.0%" in formatted 