import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.agent.context import AgentContext
from src.agent.tools.portfolio import (
    PortfolioInfoTool,
    PortfolioPerformanceTool,
    PortfolioPnLTool,
    PortfolioCashFlowTool
)
from src.agent.tools.market_data import MarketDataTool
from src.services.tinkoff.client import TinkoffClient

@pytest.fixture
def mock_tinkoff_response():
    """Mock responses from Tinkoff API."""
    return {
        "accounts": [
            {
                "id": "test_account",
                "type": "broker",
                "name": "Test Account",
                "status": "active"
            }
        ],
        "portfolio": {
            "total_amount_shares": 1000.0,
            "total_amount_bonds": 500.0,
            "total_amount_etf": 300.0,
            "expected_yield": 5.5,
            "positions": [
                {
                    "figi": "BBG000B9XRY4",
                    "instrument_type": "share",
                    "quantity": 10,
                    "average_position_price": 100.0,
                    "expected_yield": 2.5
                }
            ]
        },
        "market_data": {
            "candles": [
                {
                    "open": 100.0,
                    "high": 102.0,
                    "low": 99.0,
                    "close": 101.0,
                    "volume": 1000,
                    "time": datetime.now(),
                    "is_complete": True
                }
            ]
        }
    }

@pytest.fixture
def mock_tinkoff_client(mock_tinkoff_response):
    """Create mock Tinkoff client with predefined responses."""
    client = Mock(spec=TinkoffClient)
    
    # Setup mock responses
    client.get_accounts.return_value = mock_tinkoff_response["accounts"]
    client.get_portfolio.return_value = mock_tinkoff_response["portfolio"]
    client.get_candles.return_value = mock_tinkoff_response["market_data"]["candles"]
    
    return client

@pytest.fixture
def agent_context(mock_tinkoff_client):
    """Create agent context with mock client and tools."""
    context = AgentContext(tinkoff_client=mock_tinkoff_client)
    
    # Register portfolio tools
    portfolio_info = PortfolioInfoTool("portfolio_info", mock_tinkoff_client)
    portfolio_performance = PortfolioPerformanceTool("portfolio_performance", mock_tinkoff_client)
    portfolio_pnl = PortfolioPnLTool("portfolio_pnl", mock_tinkoff_client)
    portfolio_cash_flow = PortfolioCashFlowTool("portfolio_cash_flow", mock_tinkoff_client)
    market_data = MarketDataTool("market_data", mock_tinkoff_client)
    
    context.register_tool(portfolio_info)
    context.register_tool(portfolio_performance)
    context.register_tool(portfolio_pnl)
    context.register_tool(portfolio_cash_flow)
    context.register_tool(market_data)
    
    return context

def test_portfolio_info_tool_execution(agent_context, mock_tinkoff_response):
    """Test portfolio info tool execution."""
    # Execute portfolio tool
    result = agent_context.execute_tool("portfolio_info", account_id="test_account")
    
    # Verify the tool called Tinkoff client correctly
    agent_context.tinkoff_client.get_portfolio.assert_called_once_with("test_account")
    
    # Verify result matches mock response
    assert result["total_amount_shares"] == mock_tinkoff_response["portfolio"]["total_amount_shares"]
    assert result["positions"] == mock_tinkoff_response["portfolio"]["positions"]

def test_portfolio_performance_tool_execution(agent_context, mock_tinkoff_response):
    """Test portfolio performance tool execution."""
    # Execute portfolio tool
    result = agent_context.execute_tool(
        "portfolio_performance",
        account_id="test_account",
        period="1w"
    )
    
    # Verify the tool called Tinkoff client correctly
    agent_context.tinkoff_client.get_portfolio.assert_called()
    
    # Basic validation of performance metrics
    assert "metrics" in result
    assert "absolute_return" in result["metrics"]
    assert "relative_return" in result["metrics"]

def test_market_data_tool_execution(agent_context, mock_tinkoff_response):
    """Test market data tool execution."""
    # Test parameters
    figi = "BBG000B9XRY4"
    from_date = datetime.now() - timedelta(days=7)
    to_date = datetime.now()
    
    # Execute market data tool
    result = agent_context.execute_tool(
        "market_data",
        figi=figi,
        from_date=from_date,
        to_date=to_date
    )
    
    # Verify the tool called Tinkoff client correctly
    agent_context.tinkoff_client.get_candles.assert_called_once()
    call_args = agent_context.tinkoff_client.get_candles.call_args[1]
    assert call_args["figi"] == figi
    assert call_args["from_date"] == from_date
    assert call_args["to_date"] == to_date
    
    # Verify result matches mock response
    assert result == mock_tinkoff_response["market_data"]["candles"]

@pytest.mark.asyncio
async def test_async_market_data_streaming(agent_context):
    """Test asynchronous market data streaming."""
    # Mock streaming data
    mock_stream_data = [
        {"price": 100.0, "time": datetime.now()},
        {"price": 101.0, "time": datetime.now()},
        {"price": 102.0, "time": datetime.now()}
    ]
    
    # Setup mock async generator
    async def mock_stream():
        for data in mock_stream_data:
            yield data
    
    agent_context.tinkoff_client.stream_market_data = mock_stream
    
    # Execute streaming
    received_data = []
    async for data in agent_context.execute_tool_async(
        "market_data_stream",
        figi="BBG000B9XRY4"
    ):
        received_data.append(data)
        if len(received_data) == len(mock_stream_data):
            break
    
    # Verify received data
    assert received_data == mock_stream_data

def test_error_handling_integration(agent_context):
    """Test error handling in integration scenario."""
    # Setup error response
    agent_context.tinkoff_client.get_portfolio.side_effect = ValueError("API Error")
    
    # Execute tool and verify error handling
    with pytest.raises(ValueError) as exc_info:
        agent_context.execute_tool("portfolio_info", account_id="test_account")
    assert str(exc_info.value) == "API Error"

def test_tool_chain_execution(agent_context, mock_tinkoff_response):
    """Test execution of multiple tools in sequence."""
    # First get portfolio info
    portfolio = agent_context.execute_tool("portfolio_info", account_id="test_account")
    
    # Then get market data for first position
    figi = portfolio["positions"][0]["figi"]
    market_data = agent_context.execute_tool(
        "market_data",
        figi=figi,
        from_date=datetime.now() - timedelta(days=1),
        to_date=datetime.now()
    )
    
    # Finally get performance metrics
    performance = agent_context.execute_tool(
        "portfolio_performance",
        account_id="test_account",
        period="1d"
    )
    
    # Verify all tools executed correctly
    assert portfolio["positions"] == mock_tinkoff_response["portfolio"]["positions"]
    assert market_data == mock_tinkoff_response["market_data"]["candles"]
    assert "metrics" in performance

def test_context_state_integration(agent_context, mock_tinkoff_response):
    """Test integration with context state."""
    # Execute portfolio tool and store result in context
    result = agent_context.execute_tool("portfolio_info", account_id="test_account")
    agent_context.set_state("last_portfolio", result)
    
    # Verify state was updated
    stored_portfolio = agent_context.get_state("last_portfolio")
    assert stored_portfolio == result
    assert stored_portfolio["positions"] == mock_tinkoff_response["portfolio"]["positions"]

def test_conversation_history_integration(agent_context):
    """Test integration with conversation history."""
    # Execute tool and add result to history
    result = agent_context.execute_tool("portfolio_info", account_id="test_account")
    
    agent_context.add_to_history({
        "role": "system",
        "content": f"Retrieved portfolio data: {result}",
        "timestamp": datetime.now()
    })
    
    # Verify history was updated
    assert len(agent_context.conversation_history) == 1
    assert "Retrieved portfolio data" in agent_context.conversation_history[0]["content"] 