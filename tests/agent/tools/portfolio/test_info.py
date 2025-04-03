"""
Tests for portfolio info tool.
"""

from datetime import datetime
from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock

from src.agent.tools.portfolio.info import PortfolioInfoTool
from src.services.tinkoff.models import Currency, InstrumentType, MoneyAmount, Portfolio, Position
from src.models.base import Tool


@pytest.fixture
def mock_portfolio_service():
    """Create mock portfolio service."""
    service = Mock()
    service.get_accounts = AsyncMock()
    service.get_portfolio = AsyncMock()
    service.get_positions_by_type = AsyncMock()
    service.get_cash_by_currency = AsyncMock()
    return service


@pytest.fixture
def portfolio_info_tool(mock_portfolio_service):
    """Create portfolio info tool with mock service."""
    tool_config = Tool(
        name="portfolio_info",
        type="portfolio",
        description="Get portfolio info",
        parameters={
            "account_id": {
                "type": "string",
                "description": "Portfolio account ID",
                "required": False,
            },
            "instrument_type": {
                "type": "string",
                "description": "Filter positions by instrument type",
                "required": False,
            },
            "currency": {
                "type": "string",
                "description": "Filter cash balance by currency",
                "required": False,
            },
        },
        required_parameters=[]
    )
    tool = PortfolioInfoTool(mock_portfolio_service)
    tool.config = tool_config
    return tool


@pytest.fixture
def sample_position():
    """Create sample position data."""
    return Position(
        figi="BBG000B9XRY4",
        instrument_type=InstrumentType.STOCK,
        quantity=Decimal("10"),
        average_price=MoneyAmount(
            currency=Currency.USD,
            value=Decimal("150.50")
        ),
        current_price=MoneyAmount(
            currency=Currency.USD,
            value=Decimal("155.75")
        ),
        current_value=MoneyAmount(
            currency=Currency.USD,
            value=Decimal("1557.50")
        ),
        expected_yield=MoneyAmount(
            currency=Currency.USD,
            value=Decimal("52.50")
        )
    )


@pytest.fixture
def sample_portfolio(sample_position):
    """Create sample portfolio data."""
    return Portfolio(
        account_id="test_account",
        total_amount=MoneyAmount(
            currency=Currency.USD,
            value=Decimal("10000.00")
        ),
        expected_yield=MoneyAmount(
            currency=Currency.USD,
            value=Decimal("500.00")
        ),
        positions=[sample_position],
        cash=[
            MoneyAmount(
                currency=Currency.USD,
                value=Decimal("1000.00")
            ),
            MoneyAmount(
                currency=Currency.RUB,
                value=Decimal("50000.00")
            )
        ],
        updated_at=datetime.now()
    )


@pytest.mark.asyncio
async def test_get_portfolio_info_success(portfolio_info_tool, mock_portfolio_service, sample_portfolio):
    """Test successful portfolio info retrieval."""
    # Setup mock
    mock_portfolio_service.get_accounts.return_value = ["test_account"]
    mock_portfolio_service.get_portfolio.return_value = sample_portfolio
    
    # Execute tool
    result = await portfolio_info_tool.execute()
    
    # Verify result
    assert result["account_id"] == "test_account"
    assert result["portfolio"] == sample_portfolio
    
    # Verify service calls
    mock_portfolio_service.get_accounts.assert_called_once()
    mock_portfolio_service.get_portfolio.assert_called_once_with("test_account")


@pytest.mark.asyncio
async def test_get_portfolio_info_with_account(portfolio_info_tool, mock_portfolio_service, sample_portfolio):
    """Test portfolio info retrieval with specific account."""
    # Setup mock
    mock_portfolio_service.get_portfolio.return_value = sample_portfolio
    
    # Execute tool
    result = await portfolio_info_tool.execute(account_id="specific_account")
    
    # Verify result
    assert result["account_id"] == "specific_account"
    assert result["portfolio"] == sample_portfolio
    
    # Verify service calls
    mock_portfolio_service.get_accounts.assert_not_called()
    mock_portfolio_service.get_portfolio.assert_called_once_with("specific_account")


@pytest.mark.asyncio
async def test_get_portfolio_info_no_accounts(portfolio_info_tool, mock_portfolio_service):
    """Test portfolio info retrieval with no accounts."""
    # Setup mock
    mock_portfolio_service.get_accounts.return_value = []
    
    # Execute tool
    result = await portfolio_info_tool.execute()
    
    # Verify result
    assert "error" in result
    assert result["error"] == "No accounts found"
    
    # Verify service calls
    mock_portfolio_service.get_accounts.assert_called_once()
    mock_portfolio_service.get_portfolio.assert_not_called()


@pytest.mark.asyncio
async def test_get_portfolio_by_instrument_type(portfolio_info_tool, mock_portfolio_service, sample_position):
    """Test portfolio info retrieval filtered by instrument type."""
    # Setup mock
    mock_portfolio_service.get_accounts.return_value = ["test_account"]
    mock_portfolio_service.get_positions_by_type.return_value = [sample_position]
    
    # Execute tool
    result = await portfolio_info_tool.execute_with_instrument_type(
        account_id="test_account",
        instrument_type="STOCK"  # Use uppercase as defined in InstrumentType
    )
    
    # Verify result
    assert "positions" in result
    assert len(result["positions"]) == 1
    assert result["positions"][0]["type"] == "stock"
    
    # Verify service calls
    mock_portfolio_service.get_positions_by_type.assert_called_once_with(
        "test_account", InstrumentType.STOCK
    )


@pytest.mark.asyncio
async def test_get_portfolio_by_invalid_instrument_type(portfolio_info_tool, mock_portfolio_service):
    """Test portfolio info retrieval with invalid instrument type."""
    # Setup mock
    mock_portfolio_service.get_accounts.return_value = ["test_account"]
    
    # Execute tool
    result = await portfolio_info_tool.execute_with_instrument_type(
        instrument_type="INVALID"
    )
    
    # Verify result
    assert "error" in result
    assert "Invalid instrument type" in result["error"]
    
    # Verify service calls
    mock_portfolio_service.get_accounts.assert_called_once()
    mock_portfolio_service.get_positions_by_type.assert_not_called()


@pytest.mark.asyncio
async def test_get_portfolio_by_currency(portfolio_info_tool, mock_portfolio_service):
    """Test portfolio info retrieval filtered by currency."""
    # Setup mock
    mock_portfolio_service.get_accounts.return_value = ["test_account"]
    mock_portfolio_service.get_cash_by_currency.return_value = MoneyAmount(
        currency=Currency.USD,
        value=Decimal("1000.00")
    )
    
    # Execute tool
    result = await portfolio_info_tool.execute_with_currency(
        currency="USD"
    )
    
    # Verify result
    assert "cash" in result
    assert result["cash"]["currency"] == "USD"
    assert result["cash"]["value"] == "1000.00"
    
    # Verify service calls
    mock_portfolio_service.get_accounts.assert_called_once()
    mock_portfolio_service.get_cash_by_currency.assert_called_once_with(
        "test_account", Currency.USD
    )


@pytest.mark.asyncio
async def test_get_portfolio_by_invalid_currency(portfolio_info_tool, mock_portfolio_service):
    """Test portfolio info retrieval with invalid currency."""
    # Setup mock
    mock_portfolio_service.get_accounts.return_value = ["test_account"]
    
    # Execute tool
    result = await portfolio_info_tool.execute_with_currency(
        currency="INVALID"
    )
    
    # Verify result
    assert "error" in result
    assert "Invalid currency" in result["error"]
    
    # Verify service calls
    mock_portfolio_service.get_accounts.assert_called_once()
    mock_portfolio_service.get_cash_by_currency.assert_not_called()


@pytest.mark.asyncio
async def test_format_portfolio(portfolio_info_tool, sample_portfolio):
    """Test portfolio formatting."""
    # Format portfolio
    result = await portfolio_info_tool._format_portfolio(sample_portfolio)
    
    # Verify result structure
    assert result["account_id"] == sample_portfolio.account_id
    assert result["total_amount"]["value"] == str(sample_portfolio.total_amount.value)
    assert result["total_amount"]["currency"] == sample_portfolio.total_amount.currency.value
    assert result["expected_yield"]["value"] == str(sample_portfolio.expected_yield.value)
    assert result["expected_yield"]["currency"] == sample_portfolio.expected_yield.currency.value
    assert len(result["positions"]) == len(sample_portfolio.positions)
    assert len(result["cash"]) == len(sample_portfolio.cash)
    assert "updated_at" in result
    assert result["updated_at"] == sample_portfolio.updated_at.isoformat()


@pytest.mark.asyncio
async def test_format_position(portfolio_info_tool, sample_position):
    """Test position formatting."""
    # Format position
    result = await portfolio_info_tool._format_position(sample_position)
    
    # Verify result structure
    assert result["figi"] == sample_position.figi
    assert result["type"] == sample_position.instrument_type.value
    assert result["quantity"] == str(sample_position.quantity)
    assert result["average_price"]["value"] == str(sample_position.average_price.value)
    assert result["average_price"]["currency"] == sample_position.average_price.currency.value
    assert result["current_price"]["value"] == str(sample_position.current_price.value)
    assert result["current_price"]["currency"] == sample_position.current_price.currency.value
    assert result["current_value"]["value"] == str(sample_position.current_value.value)
    assert result["current_value"]["currency"] == sample_position.current_value.currency.value
    assert result["expected_yield"]["value"] == str(sample_position.expected_yield.value)
    assert result["expected_yield"]["currency"] == sample_position.expected_yield.currency.value 