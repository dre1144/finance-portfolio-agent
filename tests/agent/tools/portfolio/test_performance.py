"""
Tests for portfolio performance tool.
"""

from datetime import datetime, timedelta
from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock

from src.agent.tools.portfolio.performance import PortfolioPerformanceTool
from src.models.base import Message, Tool, ToolType
from src.services.tinkoff.models import Currency, InstrumentType, MoneyAmount, Portfolio, Position


@pytest.fixture
def mock_portfolio_service():
    """Create a mock portfolio service."""
    return Mock()


@pytest.fixture
def portfolio_performance_tool(mock_portfolio_service):
    """Create a PortfolioPerformanceTool instance."""
    return PortfolioPerformanceTool(mock_portfolio_service)


@pytest.fixture
def sample_historical_data():
    """Create sample historical portfolio data."""
    return [
        {
            "date": datetime(2024, 1, 1),
            "total_value": MoneyAmount(currency=Currency.RUB, value=Decimal("100000")),
            "positions": [
                {
                    "figi": "BBG000B9XRY4",
                    "instrument_type": InstrumentType.STOCK,
                    "value": MoneyAmount(currency=Currency.USD, value=Decimal("1502.50")),
                },
                {
                    "figi": "BBG00NRFC2X2",
                    "instrument_type": InstrumentType.BOND,
                    "value": MoneyAmount(currency=Currency.RUB, value=Decimal("50000")),
                },
            ],
            "cash": [
                MoneyAmount(currency=Currency.RUB, value=Decimal("30000")),
                MoneyAmount(currency=Currency.USD, value=Decimal("500")),
            ],
        },
        {
            "date": datetime(2024, 1, 15),
            "total_value": MoneyAmount(currency=Currency.RUB, value=Decimal("105000")),
            "positions": [
                {
                    "figi": "BBG000B9XRY4",
                    "instrument_type": InstrumentType.STOCK,
                    "value": MoneyAmount(currency=Currency.USD, value=Decimal("1555.00")),
                },
                {
                    "figi": "BBG00NRFC2X2",
                    "instrument_type": InstrumentType.BOND,
                    "value": MoneyAmount(currency=Currency.RUB, value=Decimal("51000")),
                },
            ],
            "cash": [
                MoneyAmount(currency=Currency.RUB, value=Decimal("30000")),
                MoneyAmount(currency=Currency.USD, value=Decimal("500")),
            ],
        },
    ]


def test_tool_initialization(portfolio_performance_tool):
    """Test tool initialization and configuration."""
    assert isinstance(portfolio_performance_tool.config, Tool)
    assert portfolio_performance_tool.config.name == "portfolio_performance"
    assert portfolio_performance_tool.config.type == ToolType.PORTFOLIO
    assert "account_id" in portfolio_performance_tool.config.parameters
    assert "instrument_type" in portfolio_performance_tool.config.parameters
    assert "currency" in portfolio_performance_tool.config.parameters
    assert "period" in portfolio_performance_tool.config.parameters


def test_extract_parameters(portfolio_performance_tool):
    """Test parameter extraction from message."""
    message = Message(
        content="Get portfolio performance",
        metadata={
            "account_id": "test_account",
            "instrument_type": "STOCK",
            "currency": "USD",
            "period": "month",
        },
    )
    
    params = portfolio_performance_tool.extract_parameters(message)
    
    assert params["account_id"] == "test_account"
    assert params["instrument_type"] == "STOCK"
    assert params["currency"] == "USD"
    assert params["period"] == "month"


def test_extract_parameters_with_defaults(portfolio_performance_tool):
    """Test parameter extraction with default values."""
    message = Message(
        content="Get portfolio performance",
        metadata={
            "account_id": "test_account",
        },
    )
    
    params = portfolio_performance_tool.extract_parameters(message)
    
    assert params["account_id"] == "test_account"
    assert params["currency"] == "RUB"  # Default value
    assert params["period"] == "all"    # Default value


def test_get_period_start(portfolio_performance_tool):
    """Test period start calculation."""
    with patch("src.agent.tools.portfolio.performance.datetime") as mock_datetime:
        now = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = now
        
        day_start = portfolio_performance_tool._get_period_start("day")
        assert (now - day_start) <= timedelta(days=1, seconds=1)
        assert (now - day_start) >= timedelta(days=1)
        
        week_start = portfolio_performance_tool._get_period_start("week")
        assert (now - week_start) <= timedelta(weeks=1, seconds=1)
        assert (now - week_start) >= timedelta(weeks=1)
        
        month_start = portfolio_performance_tool._get_period_start("month")
        assert (now - month_start) <= timedelta(days=30, seconds=1)
        assert (now - month_start) >= timedelta(days=30)
        
        year_start = portfolio_performance_tool._get_period_start("year")
        assert (now - year_start) <= timedelta(days=365, seconds=1)
        assert (now - year_start) >= timedelta(days=365)
        
        assert portfolio_performance_tool._get_period_start("all") is None
        
        with pytest.raises(ValueError):
            portfolio_performance_tool._get_period_start("invalid")


def test_calculate_metrics(portfolio_performance_tool, sample_historical_data):
    """Test performance metrics calculation."""
    absolute_return, relative_return, annualized_return, volatility = (
        portfolio_performance_tool._calculate_metrics(sample_historical_data)
    )
    
    assert absolute_return == Decimal("5000")  # 105000 - 100000
    assert relative_return == Decimal("5")     # (5000 / 100000) * 100
    assert annualized_return > Decimal("0")    # Should be positive
    assert volatility >= Decimal("0")          # Should be non-negative


def test_calculate_metrics_insufficient_data(portfolio_performance_tool):
    """Test metrics calculation with insufficient data."""
    # Test with empty data
    metrics = portfolio_performance_tool._calculate_metrics([])
    assert all(m == Decimal("0") for m in metrics)
    
    # Test with single data point
    metrics = portfolio_performance_tool._calculate_metrics([{
        "date": datetime(2024, 1, 1),
        "total_value": MoneyAmount(currency=Currency.RUB, value=Decimal("100000")),
        "positions": [],
        "cash": [],
    }])
    assert all(m == Decimal("0") for m in metrics)


@pytest.mark.asyncio
async def test_execute_success(portfolio_performance_tool, mock_portfolio_service, sample_historical_data):
    """Test successful tool execution."""
    # Setup mock
    mock_portfolio_service.get_accounts.return_value = ["test_account"]
    
    # Create message with parameters
    message = Message(
        content="Get portfolio performance",
        metadata={
            "account_id": "test_account",
            "currency": "RUB",
            "period": "month",
        },
    )
    
    # Execute tool
    result = await portfolio_performance_tool.execute(message, {})
    
    # Verify result structure
    assert "metrics" in result
    assert "absolute_return" in result["metrics"]
    assert "relative_return" in result["metrics"]
    assert "annualized_return" in result["metrics"]
    assert "volatility" in result["metrics"]
    assert result["metrics"]["currency"] == "RUB"


@pytest.mark.asyncio
async def test_execute_with_instrument_type(portfolio_performance_tool, mock_portfolio_service):
    """Test tool execution with instrument type filter."""
    # Setup mock
    mock_portfolio_service.get_accounts.return_value = ["test_account"]
    
    # Create message with instrument type
    message = Message(
        content="Get portfolio performance",
        metadata={
            "account_id": "test_account",
            "instrument_type": "STOCK",
            "currency": "RUB",
            "period": "month",
        },
    )
    
    # Execute tool
    result = await portfolio_performance_tool.execute(message, {})
    
    # Verify result
    assert "metrics" in result
    assert result["metrics"]["currency"] == "RUB"


@pytest.mark.asyncio
async def test_execute_no_accounts(portfolio_performance_tool, mock_portfolio_service):
    """Test tool execution with no accounts."""
    # Setup mock
    mock_portfolio_service.get_accounts.return_value = []
    
    # Create message
    message = Message(
        content="Get portfolio performance",
        metadata={},
    )
    
    # Execute tool
    result = await portfolio_performance_tool.execute(message, {})
    
    # Verify result
    assert "error" in result
    assert result["error"] == "No accounts found"


@pytest.mark.asyncio
async def test_get_historical_data(portfolio_performance_tool):
    """Test getting historical data."""
    data = await portfolio_performance_tool._get_historical_data(
        account_id="123",
        period_start=None,
        target_currency=Currency.RUB,
    )
    
    assert len(data) == 2
    
    # Test first data point
    first = data[0]
    assert first["date"] == datetime(2024, 1, 1)
    assert first["total_value"].value == Decimal("100000")
    assert len(first["positions"]) == 2
    assert len(first["cash"]) == 2
    
    # Test second data point
    second = data[1]
    assert second["date"] == datetime(2024, 1, 15)
    assert second["total_value"].value == Decimal("105000")


@pytest.mark.asyncio
async def test_get_historical_data_with_filters(portfolio_performance_tool):
    """Test getting historical data with filters."""
    # Test period filter
    period_start = datetime(2024, 1, 10)
    data = await portfolio_performance_tool._get_historical_data(
        account_id="123",
        period_start=period_start,
        target_currency=Currency.RUB,
    )
    assert len(data) == 1
    assert data[0]["date"] >= period_start
    
    # Test instrument type filter
    data = await portfolio_performance_tool._get_historical_data(
        account_id="123",
        period_start=None,
        target_currency=Currency.RUB,
        instrument_type=InstrumentType.STOCK,
    )
    assert len(data) == 2
    assert all(
        p["instrument_type"] == InstrumentType.STOCK
        for d in data
        for p in d["positions"]
    )


def test_format_metrics(portfolio_performance_tool):
    """Test metrics formatting."""
    formatted = portfolio_performance_tool._format_metrics(
        absolute_return=Decimal("5000"),
        relative_return=Decimal("5"),
        annualized_return=Decimal("130"),
        volatility=Decimal("10"),
        currency=Currency.RUB,
    )
    
    assert formatted["absolute_return"]["value"] == "5000"
    assert formatted["absolute_return"]["currency"] == "RUB"
    assert formatted["relative_return"] == "5"
    assert formatted["annualized_return"] == "130"
    assert formatted["volatility"] == "10"


@pytest.mark.asyncio
async def test_execute_no_account_id(portfolio_performance_tool, mock_portfolio_service):
    """Test executing tool without account ID."""
    # Setup mock
    mock_portfolio_service.get_accounts.return_value = ["123"]
    
    # Create message
    message = Message(
        content="Get portfolio performance",
        metadata={},
    )
    
    # Execute tool
    result = await portfolio_performance_tool.execute(message, {})
    
    # Verify result
    assert "account_id" in result
    assert result["account_id"] == "123"
    assert "metrics" in result


@pytest.mark.asyncio
async def test_execute_with_account_id(portfolio_performance_tool, mock_portfolio_service):
    """Test executing tool with account ID."""
    # Create message
    message = Message(
        content="Get portfolio performance",
        metadata={"account_id": "456"},
    )
    
    # Execute tool
    result = await portfolio_performance_tool.execute(message, {})
    
    # Verify result
    assert "account_id" in result
    assert result["account_id"] == "456"
    assert "metrics" in result


@pytest.mark.asyncio
async def test_execute_with_filters(portfolio_performance_tool, mock_portfolio_service):
    """Test executing tool with filters."""
    # Create message
    message = Message(
        content="Get portfolio performance",
        metadata={
            "account_id": "123",
            "instrument_type": "STOCK",
            "currency": "USD",
            "period": "month",
        },
    )
    
    # Execute tool
    result = await portfolio_performance_tool.execute(message, {})
    
    # Verify result
    assert "account_id" in result
    assert result["account_id"] == "123"
    assert "metrics" in result
    assert result["metrics"]["currency"] == "USD"


@pytest.mark.asyncio
async def test_execute_empty_data(portfolio_performance_tool, mock_portfolio_service):
    """Test executing tool with empty historical data."""
    # Create message
    message = Message(
        content="Get portfolio performance",
        metadata={"account_id": "123"},
    )
    
    # Mock empty historical data
    with patch.object(portfolio_performance_tool, "_get_historical_data", return_value=[]):
        result = await portfolio_performance_tool.execute(message, {})
    
    # Verify result
    assert "metrics" in result
    assert result["metrics"]["absolute_return"]["value"] == "0"
    assert result["metrics"]["relative_return"] == "0"
    assert result["metrics"]["annualized_return"] == "0"
    assert result["metrics"]["volatility"] == "0" 