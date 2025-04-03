"""Tests for PortfolioCashFlowTool."""

from datetime import datetime, timedelta
from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agent.tools.portfolio.cash_flow import PortfolioCashFlowTool
from src.models.base import Message
from src.services.tinkoff.models import Currency, InstrumentType, MoneyAmount


@pytest.fixture
def portfolio_service():
    """Create a mock portfolio service."""
    service = AsyncMock()
    service.get_accounts = AsyncMock(return_value=["test_account"])
    return service


@pytest.fixture
def tool(portfolio_service):
    """Create a PortfolioCashFlowTool instance."""
    return PortfolioCashFlowTool(portfolio_service)


def test_tool_initialization(tool):
    """Test tool initialization."""
    assert tool.config.name == "portfolio_cash_flow"
    assert tool.config.type == "portfolio"
    assert tool.config.description == "Get cash flow information for the portfolio"
    assert "account_id" in tool.config.parameters
    assert "instrument_type" in tool.config.parameters
    assert "currency" in tool.config.parameters
    assert "period" in tool.config.parameters
    assert "flow_type" in tool.config.parameters


def test_extract_parameters_with_defaults(tool):
    """Test parameter extraction with defaults."""
    message = Message(content="Get cash flows")
    params = tool.extract_parameters(message)
    
    assert params["currency"] == "RUB"
    assert params["period"] == "all"
    assert params["flow_type"] == "all"


def test_extract_parameters_from_metadata(tool):
    """Test parameter extraction from message metadata."""
    message = Message(
        content="Get cash flows",
        metadata={
            "account_id": "test_account",
            "instrument_type": "STOCK",
            "currency": "USD",
            "period": "month",
            "flow_type": "dividend",
        }
    )
    params = tool.extract_parameters(message)
    
    assert params["account_id"] == "test_account"
    assert params["instrument_type"] == "STOCK"
    assert params["currency"] == "USD"
    assert params["period"] == "month"
    assert params["flow_type"] == "dividend"


def test_get_period_start_day(tool):
    """Test period start calculation for day period."""
    now = datetime.now()
    start = tool._get_period_start("day")
    assert isinstance(start, datetime)
    assert now - start < timedelta(days=1, minutes=1)
    assert now - start > timedelta(days=1, minutes=-1)


def test_get_period_start_all(tool):
    """Test period start calculation for all period."""
    start = tool._get_period_start("all")
    assert start is None


def test_get_period_start_invalid(tool):
    """Test period start calculation with invalid period."""
    with pytest.raises(ValueError, match="Invalid period: invalid"):
        tool._get_period_start("invalid")


def test_validate_flow_type_valid(tool):
    """Test flow type validation with valid types."""
    valid_types = ["dividend", "coupon", "trade", "tax", "commission", "all"]
    for flow_type in valid_types:
        tool._validate_flow_type(flow_type)


def test_validate_flow_type_invalid(tool):
    """Test flow type validation with invalid type."""
    with pytest.raises(ValueError, match="Invalid flow type: invalid"):
        tool._validate_flow_type("invalid")


@pytest.mark.asyncio
async def test_get_cash_flows_no_filters(tool):
    """Test cash flow retrieval without filters."""
    flows = await tool._get_cash_flows(
        account_id="test_account",
        period_start=None,
        target_currency=Currency.RUB,
    )
    
    assert len(flows) == 3
    assert all(isinstance(f["amount"], MoneyAmount) for f in flows)
    assert all(isinstance(f["commission"], MoneyAmount) for f in flows)
    assert all(isinstance(f["tax"], MoneyAmount) for f in flows)


@pytest.mark.asyncio
async def test_get_cash_flows_with_period(tool):
    """Test cash flow retrieval with period filter."""
    now = datetime.now()
    flows = await tool._get_cash_flows(
        account_id="test_account",
        period_start=now - timedelta(days=1),
        target_currency=Currency.RUB,
    )
    
    assert len(flows) == 0  # All mock flows are from January 2024


@pytest.mark.asyncio
async def test_get_cash_flows_with_instrument_type(tool):
    """Test cash flow retrieval with instrument type filter."""
    flows = await tool._get_cash_flows(
        account_id="test_account",
        period_start=None,
        target_currency=Currency.RUB,
        instrument_type=InstrumentType.STOCK,
    )
    
    assert len(flows) == 2
    assert all(f["instrument_type"] == InstrumentType.STOCK for f in flows)


@pytest.mark.asyncio
async def test_get_cash_flows_with_flow_type(tool):
    """Test cash flow retrieval with flow type filter."""
    flows = await tool._get_cash_flows(
        account_id="test_account",
        period_start=None,
        target_currency=Currency.RUB,
        flow_type="dividend",
    )
    
    assert len(flows) == 1
    assert flows[0]["type"] == "dividend"


def test_format_flow(tool):
    """Test cash flow formatting."""
    flow = {
        "date": datetime(2024, 1, 1, 12, 0),
        "type": "dividend",
        "instrument_type": InstrumentType.STOCK,
        "figi": "BBG000B9XRY4",
        "amount": MoneyAmount(currency=Currency.USD, value=Decimal("10.50")),
        "commission": MoneyAmount(currency=Currency.USD, value=Decimal("0.50")),
        "tax": MoneyAmount(currency=Currency.USD, value=Decimal("1.50")),
    }
    
    formatted = tool._format_flow(flow)
    
    assert formatted["date"] == "2024-01-01T12:00:00"
    assert formatted["type"] == "dividend"
    assert formatted["instrument_type"] == "stock"
    assert formatted["figi"] == "BBG000B9XRY4"
    assert formatted["amount"]["value"] == "10.50"
    assert formatted["amount"]["currency"] == "USD"
    assert formatted["commission"]["value"] == "0.50"
    assert formatted["commission"]["currency"] == "USD"
    assert formatted["tax"]["value"] == "1.50"
    assert formatted["tax"]["currency"] == "USD"


@pytest.mark.asyncio
async def test_execute_success(tool):
    """Test successful tool execution."""
    message = Message(
        content="Get cash flows",
        metadata={
            "account_id": "test_account",
            "currency": "USD",
        }
    )
    
    result = await tool.execute(message, {})
    
    assert result["account_id"] == "test_account"
    assert result["currency"] == "USD"
    assert result["period"] == "all"
    assert result["flow_type"] == "all"
    assert "totals" in result
    assert "flows" in result
    assert len(result["flows"]) == 3


@pytest.mark.asyncio
async def test_execute_no_accounts(tool, portfolio_service):
    """Test execution when no accounts are available."""
    portfolio_service.get_accounts.return_value = []
    message = Message(content="Get cash flows")
    
    result = await tool.execute(message, {})
    
    assert result["error"] == "No accounts found"


@pytest.mark.asyncio
async def test_execute_invalid_flow_type(tool):
    """Test execution with invalid flow type."""
    message = Message(
        content="Get cash flows",
        metadata={"flow_type": "invalid"}
    )
    
    result = await tool.execute(message, {})
    
    assert result["error"] == "Invalid flow type: invalid"


@pytest.mark.asyncio
async def test_execute_invalid_instrument_type(tool):
    """Test execution with invalid instrument type."""
    message = Message(
        content="Get cash flows",
        metadata={"instrument_type": "invalid"}
    )
    
    result = await tool.execute(message, {})
    
    assert "error" in result 