"""
Tests for portfolio PnL tool.
"""

from datetime import datetime, timedelta
from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock

from src.agent.tools.portfolio.pnl import PortfolioPnLTool
from src.models.base import Message, Tool, ToolType
from src.services.tinkoff.models import Currency, InstrumentType, MoneyAmount, Position


@pytest.fixture
def mock_portfolio_service():
    """Create a mock portfolio service."""
    return AsyncMock()


@pytest.fixture
def portfolio_pnl_tool(mock_portfolio_service):
    """Create a PortfolioPnLTool instance."""
    return PortfolioPnLTool(mock_portfolio_service)


@pytest.fixture
def sample_position():
    """Create a sample position."""
    return Position(
        figi="BBG000B9XRY4",
        instrument_type=InstrumentType.STOCK,
        quantity=Decimal("10"),
        average_price=MoneyAmount(currency=Currency.USD, value=Decimal("150.25")),
        current_price=MoneyAmount(currency=Currency.USD, value=Decimal("155.50")),
        current_value=MoneyAmount(currency=Currency.USD, value=Decimal("1555.00")),
        expected_yield=MoneyAmount(currency=Currency.USD, value=Decimal("52.50")),
    )


@pytest.fixture
def sample_operations():
    """Create sample operations."""
    return [
        {
            "date": datetime(2024, 1, 1),
            "type": "BUY",
            "figi": "BBG000B9XRY4",
            "instrument_type": InstrumentType.STOCK,
            "quantity": 10,
            "price": MoneyAmount(currency=Currency.USD, value=Decimal("150.25")),
            "payment": MoneyAmount(currency=Currency.USD, value=Decimal("-1502.50")),
        },
        {
            "date": datetime(2024, 1, 15),
            "type": "SELL",
            "figi": "BBG000B9XRY4",
            "instrument_type": InstrumentType.STOCK,
            "quantity": 5,
            "price": MoneyAmount(currency=Currency.USD, value=Decimal("155.50")),
            "payment": MoneyAmount(currency=Currency.USD, value=Decimal("777.50")),
        },
        {
            "date": datetime(2024, 1, 20),
            "type": "DIVIDEND",
            "figi": "BBG000B9XRY4",
            "instrument_type": InstrumentType.STOCK,
            "payment": MoneyAmount(currency=Currency.USD, value=Decimal("25.00")),
        },
    ]


def test_tool_initialization(portfolio_pnl_tool):
    """Test tool initialization and configuration."""
    assert isinstance(portfolio_pnl_tool.config, Tool)
    assert portfolio_pnl_tool.config.name == "portfolio_pnl"
    assert portfolio_pnl_tool.config.type == ToolType.PORTFOLIO
    assert "account_id" in portfolio_pnl_tool.config.parameters
    assert "instrument_type" in portfolio_pnl_tool.config.parameters
    assert "currency" in portfolio_pnl_tool.config.parameters
    assert "period" in portfolio_pnl_tool.config.parameters


def test_get_period_start(portfolio_pnl_tool):
    """Test period start calculation."""
    with patch("src.agent.tools.portfolio.pnl.datetime") as mock_datetime:
        now = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = now
        
        day_start = portfolio_pnl_tool._get_period_start("day")
        assert (now - day_start) <= timedelta(days=1, seconds=1)
        assert (now - day_start) >= timedelta(days=1)
        
        week_start = portfolio_pnl_tool._get_period_start("week")
        assert (now - week_start) <= timedelta(weeks=1, seconds=1)
        assert (now - week_start) >= timedelta(weeks=1)
        
        month_start = portfolio_pnl_tool._get_period_start("month")
        assert (now - month_start) <= timedelta(days=30, seconds=1)
        assert (now - month_start) >= timedelta(days=30)
        
        year_start = portfolio_pnl_tool._get_period_start("year")
        assert (now - year_start) <= timedelta(days=365, seconds=1)
        assert (now - year_start) >= timedelta(days=365)
        
        assert portfolio_pnl_tool._get_period_start("all") is None
        
        with pytest.raises(ValueError):
            portfolio_pnl_tool._get_period_start("invalid")


@pytest.mark.asyncio
async def test_calculate_position_pnl(portfolio_pnl_tool, sample_position):
    """Test PnL calculation for a single position."""
    pnl = await portfolio_pnl_tool._calculate_position_pnl(
        position=sample_position,
        target_currency=Currency.USD,
    )
    
    # Verify PnL structure
    assert pnl["figi"] == "BBG000B9XRY4"
    assert pnl["type"] == "stock"
    assert pnl["quantity"] == "10"
    
    # Verify invested amount
    invested = pnl["invested"]
    assert invested["value"] == "1502.50"  # 10 * 150.25
    assert invested["currency"] == "USD"
    
    # Verify current value
    current = pnl["current"]
    assert current["value"] == "1555.00"
    assert current["currency"] == "USD"
    
    # Verify PnL calculations
    pnl_data = pnl["pnl"]
    assert pnl_data["absolute"]["value"] == "52.50"  # 1555.00 - 1502.50
    assert pnl_data["absolute"]["currency"] == "USD"
    assert float(pnl_data["relative"]) == pytest.approx(3.49, rel=0.01)  # (52.50 / 1502.50) * 100


@pytest.mark.asyncio
async def test_execute_success(portfolio_pnl_tool, mock_portfolio_service, sample_operations):
    """Test successful tool execution."""
    # Setup mock
    mock_portfolio_service.get_accounts.return_value = ["test_account"]
    mock_portfolio_service.get_operations.return_value = sample_operations
    
    # Create message with parameters
    message = Message(
        content="Get portfolio PnL",
        metadata={
            "account_id": "test_account",
            "currency": "USD",
            "period": "month",
        },
    )
    
    # Execute tool
    result = await portfolio_pnl_tool.execute(message, {})
    
    # Verify result structure
    assert result["account_id"] == "test_account"
    assert result["currency"] == "USD"
    assert result["period"] == "month"
    assert "total_pnl" in result
    assert result["total_pnl"]["currency"] == "USD"
    assert float(result["total_pnl"]["value"]) == pytest.approx(-725.00)  # -1502.50 + 777.50
    assert len(result["operations"]) == 3
    
    # Verify operations were called correctly
    mock_portfolio_service.get_operations.assert_called_once()


@pytest.mark.asyncio
async def test_execute_with_period(portfolio_pnl_tool, mock_portfolio_service, sample_operations):
    """Test tool execution with period filter."""
    # Setup mock
    mock_portfolio_service.get_accounts.return_value = ["test_account"]
    mock_portfolio_service.get_operations.return_value = sample_operations
    
    # Create message with period
    message = Message(
        content="Get portfolio PnL",
        metadata={
            "account_id": "test_account",
            "period": "day",
        },
    )
    
    # Execute tool
    result = await portfolio_pnl_tool.execute(message, {})
    
    # Verify result
    assert result["period"] == "day"
    assert "total_pnl" in result
    
    # Verify operations were called with correct date
    mock_portfolio_service.get_operations.assert_called_once()


@pytest.mark.asyncio
async def test_execute_no_accounts(portfolio_pnl_tool, mock_portfolio_service):
    """Test tool execution with no accounts."""
    # Setup mock
    mock_portfolio_service.get_accounts.return_value = []
    
    # Create message
    message = Message(
        content="Get portfolio PnL",
        metadata={},
    )
    
    # Execute tool
    result = await portfolio_pnl_tool.execute(message, {})
    
    # Verify result
    assert "error" in result
    assert result["error"] == "No accounts found"
    
    # Verify operations were not called
    mock_portfolio_service.get_operations.assert_not_called()


@pytest.mark.asyncio
async def test_execute_no_account_id(portfolio_pnl_tool, mock_portfolio_service, sample_operations):
    """Test executing tool without account ID."""
    # Setup mock
    mock_portfolio_service.get_accounts.return_value = ["123"]
    mock_portfolio_service.get_operations.return_value = sample_operations
    
    # Create message
    message = Message(
        content="Get portfolio PnL",
        metadata={},
    )
    
    # Execute tool
    result = await portfolio_pnl_tool.execute(message, {})
    
    # Verify result
    assert result["account_id"] == "123"
    assert "operations" in result
    assert len(result["operations"]) == 3
    
    # Verify operations were called with first account
    mock_portfolio_service.get_operations.assert_called_once()


@pytest.mark.asyncio
async def test_execute_with_instrument_type(portfolio_pnl_tool, mock_portfolio_service, sample_operations):
    """Test executing tool with instrument type filter."""
    # Setup mock
    mock_portfolio_service.get_accounts.return_value = ["test_account"]
    mock_portfolio_service.get_operations.return_value = sample_operations
    
    # Create message with instrument type
    message = Message(
        content="Get portfolio PnL",
        metadata={
            "account_id": "test_account",
            "instrument_type": "stock",
        },
    )
    
    # Execute tool
    result = await portfolio_pnl_tool.execute(message, {})
    
    # Verify result
    assert "operations" in result
    assert len(result["operations"]) == 3
    assert all(op["instrument_type"] == InstrumentType.STOCK for op in result["operations"])
    
    # Test with invalid type
    message.metadata["instrument_type"] = "invalid"
    result = await portfolio_pnl_tool.execute(message, {})
    assert "error" in result
    assert result["error"] == "Invalid instrument type: invalid" 