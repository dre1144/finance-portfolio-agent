import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.agent.context import AgentContext
from src.agent.request_handler import RequestHandler
from src.services.tinkoff.client import TinkoffClient

@pytest.fixture
def mock_tinkoff_client():
    """Create mock Tinkoff client."""
    return Mock(spec=TinkoffClient)

@pytest.fixture
def agent_context(mock_tinkoff_client):
    """Create agent context with mock client."""
    return AgentContext(tinkoff_client=mock_tinkoff_client)

@pytest.fixture
def request_handler(agent_context):
    """Create request handler."""
    return RequestHandler(agent_context)

def test_portfolio_request(request_handler, mock_tinkoff_client):
    """Test handling portfolio request."""
    # Mock portfolio data
    mock_portfolio = {
        "total_amount_shares": 1000.0,
        "positions": [
            {
                "figi": "BBG000B9XRY4",
                "name": "Apple Inc",
                "quantity": 10
            }
        ]
    }
    mock_tinkoff_client.get_portfolio.return_value = mock_portfolio
    
    # Test request
    request = {
        "type": "portfolio",
        "content": "Show me my portfolio",
        "timestamp": datetime.now()
    }
    
    response = request_handler.handle_request(request)
    
    # Verify response
    assert response["type"] == "portfolio"
    assert "portfolio" in response["content"]
    assert mock_tinkoff_client.get_portfolio.called

def test_market_data_request(request_handler, mock_tinkoff_client):
    """Test handling market data request."""
    # Mock market data
    mock_candles = [
        {
            "open": 100.0,
            "close": 101.0,
            "time": datetime.now()
        }
    ]
    mock_tinkoff_client.get_candles.return_value = mock_candles
    
    # Test request
    request = {
        "type": "market_data",
        "content": "Show me AAPL price history for last week",
        "timestamp": datetime.now()
    }
    
    response = request_handler.handle_request(request)
    
    # Verify response
    assert response["type"] == "market_data"
    assert "price history" in response["content"]
    assert mock_tinkoff_client.get_candles.called

def test_invalid_request(request_handler):
    """Test handling invalid request."""
    request = {
        "type": "invalid",
        "content": "This is an invalid request",
        "timestamp": datetime.now()
    }
    
    response = request_handler.handle_request(request)
    
    assert response["type"] == "error"
    assert "invalid request" in response["content"].lower()

def test_complex_request(request_handler, mock_tinkoff_client):
    """Test handling complex request with multiple tools."""
    # Mock data
    mock_portfolio = {
        "positions": [
            {
                "figi": "BBG000B9XRY4",
                "name": "Apple Inc",
                "quantity": 10
            }
        ]
    }
    mock_candles = [
        {
            "close": 150.0,
            "time": datetime.now()
        }
    ]
    
    mock_tinkoff_client.get_portfolio.return_value = mock_portfolio
    mock_tinkoff_client.get_candles.return_value = mock_candles
    
    # Test request
    request = {
        "type": "analysis",
        "content": "Show me my portfolio performance for AAPL",
        "timestamp": datetime.now()
    }
    
    response = request_handler.handle_request(request)
    
    # Verify response
    assert response["type"] == "analysis"
    assert mock_tinkoff_client.get_portfolio.called
    assert mock_tinkoff_client.get_candles.called

def test_request_with_parameters(request_handler, mock_tinkoff_client):
    """Test handling request with specific parameters."""
    # Test request
    request = {
        "type": "market_data",
        "content": "Show me AAPL candles for last 7 days with 1 hour interval",
        "parameters": {
            "figi": "BBG000B9XRY4",
            "interval": "1h",
            "days": 7
        },
        "timestamp": datetime.now()
    }
    
    response = request_handler.handle_request(request)
    
    # Verify correct parameters were used
    call_args = mock_tinkoff_client.get_candles.call_args[1]
    assert call_args["figi"] == "BBG000B9XRY4"
    assert call_args["interval"] == "1h"
    assert (call_args["to_date"] - call_args["from_date"]).days == 7

def test_request_error_handling(request_handler, mock_tinkoff_client):
    """Test error handling in request processing."""
    # Setup error
    mock_tinkoff_client.get_portfolio.side_effect = ValueError("API Error")
    
    # Test request
    request = {
        "type": "portfolio",
        "content": "Show me my portfolio",
        "timestamp": datetime.now()
    }
    
    response = request_handler.handle_request(request)
    
    # Verify error handling
    assert response["type"] == "error"
    assert "API Error" in response["content"]

def test_request_context_usage(request_handler, agent_context):
    """Test using context in request handling."""
    # Add some context
    agent_context.set_state("user_preferences", {"risk_profile": "conservative"})
    
    # Test request
    request = {
        "type": "recommendation",
        "content": "Suggest investments based on my profile",
        "timestamp": datetime.now()
    }
    
    response = request_handler.handle_request(request)
    
    # Verify context was used
    assert "conservative" in response["content"].lower()

def test_request_history_tracking(request_handler):
    """Test request history tracking."""
    # Make multiple requests
    requests = [
        {
            "type": "portfolio",
            "content": "Show portfolio",
            "timestamp": datetime.now()
        },
        {
            "type": "market_data",
            "content": "Show AAPL price",
            "timestamp": datetime.now()
        }
    ]
    
    for request in requests:
        request_handler.handle_request(request)
    
    # Verify history
    history = request_handler.context.conversation_history
    assert len(history) == len(requests) * 2  # Request + Response for each
    assert history[0]["content"] == "Show portfolio"

def test_request_tool_selection(request_handler):
    """Test correct tool selection based on request."""
    # Register mock tools
    class MockTool:
        def __init__(self, name):
            self.name = name
            self.called = False
        
        def execute(self, **kwargs):
            self.called = True
            return {"status": "success"}
    
    portfolio_tool = MockTool("portfolio")
    market_data_tool = MockTool("market_data")
    
    request_handler.context.register_tool(portfolio_tool)
    request_handler.context.register_tool(market_data_tool)
    
    # Test portfolio request
    request_handler.handle_request({
        "type": "portfolio",
        "content": "Show portfolio",
        "timestamp": datetime.now()
    })
    
    assert portfolio_tool.called
    assert not market_data_tool.called 