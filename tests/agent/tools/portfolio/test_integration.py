"""Integration tests for portfolio tools."""

from datetime import datetime, timedelta
from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import List, Optional

from src.agent.tools.portfolio.info import PortfolioInfoTool
from src.agent.tools.portfolio.performance import PortfolioPerformanceTool
from src.agent.tools.portfolio.pnl import PortfolioPnLTool
from src.agent.tools.portfolio.cash_flow import PortfolioCashFlowTool
from src.models.base import Message
from src.services.tinkoff.models import Currency, InstrumentType, MoneyAmount, Position, Operation, OperationType


@pytest.fixture
def mock_portfolio_service():
    """Create a mock portfolio service with test data."""
    service = AsyncMock()
    
    # Mock accounts
    service.get_accounts = AsyncMock(return_value=["test_account"])
    
    # Mock positions
    service.get_positions = AsyncMock(return_value=[
        Position(
            figi="BBG000B9XRY4",
            instrument_type=InstrumentType.STOCK,
            quantity=Decimal("10"),
            average_price=MoneyAmount(currency=Currency.USD, value=Decimal("150.25")),
            current_price=MoneyAmount(currency=Currency.USD, value=Decimal("155.50")),
            current_value=MoneyAmount(currency=Currency.USD, value=Decimal("1555.00")),
            expected_yield=MoneyAmount(currency=Currency.USD, value=Decimal("52.50")),
        ),
        Position(
            figi="BBG00NRFC2X2",
            instrument_type=InstrumentType.BOND,
            quantity=Decimal("5"),
            average_price=MoneyAmount(currency=Currency.RUB, value=Decimal("1000.00")),
            current_price=MoneyAmount(currency=Currency.RUB, value=Decimal("1020.00")),
            current_value=MoneyAmount(currency=Currency.RUB, value=Decimal("5100.00")),
            expected_yield=MoneyAmount(currency=Currency.RUB, value=Decimal("100.00")),
        ),
    ])
    
    # Mock operations
    operations = [
        Operation(
            id="op1",
            account_id="test_account",
            type=OperationType.DIVIDEND,
            instrument_id="AAPL",
            instrument_type=InstrumentType.STOCK,
            date=datetime(2024, 1, 20),
            amount=Decimal("25.00"),
            currency=Currency.USD,
            tax=Decimal("3.75")
        ),
        Operation(
            id="op2", 
            account_id="test_account",
            type=OperationType.COUPON,
            instrument_id="BOND1",
            instrument_type=InstrumentType.BOND,
            date=datetime(2024, 1, 25),
            amount=Decimal("250.00"),
            currency=Currency.USD,
            tax=Decimal("32.50")
        ),
        Operation(
            id="op3",
            account_id="test_account",
            type=OperationType.SELL,
            instrument_id="MSFT",
            instrument_type=InstrumentType.STOCK,
            date=datetime(2024, 1, 15),
            amount=Decimal("777.50"),
            currency=Currency.USD,
            commission=Decimal("7.50")
        ),
        Operation(
            id="op4",
            account_id="test_account",
            type=OperationType.BUY,
            instrument_id="GOOGL",
            instrument_type=InstrumentType.STOCK,
            date=datetime(2024, 1, 10),
            amount=Decimal("1500.00"),
            currency=Currency.USD,
            commission=Decimal("10.00")
        ),
        Operation(
            id="op5",
            account_id="test_account",
            type=OperationType.BUY,
            instrument_id="AMZN",
            instrument_type=InstrumentType.STOCK,
            date=datetime(2024, 1, 5),
            amount=Decimal("2000.00"),
            currency=Currency.USD,
            commission=Decimal("12.50")
        )
    ]
    service.get_operations = AsyncMock(return_value=operations)
    
    # Mock historical data
    historical_data = {
        "BBG000B9XRY4": [
            {
                "date": datetime(2024, 1, 1),
                "close": MoneyAmount(currency=Currency.USD, value=Decimal("150.25")),
            },
            {
                "date": datetime(2024, 1, 15),
                "close": MoneyAmount(currency=Currency.USD, value=Decimal("155.50")),
            },
            {
                "date": datetime(2024, 1, 30),
                "close": MoneyAmount(currency=Currency.USD, value=Decimal("155.50")),
            },
        ],
        "BBG00NRFC2X2": [
            {
                "date": datetime(2024, 1, 10),
                "close": MoneyAmount(currency=Currency.RUB, value=Decimal("1000.00")),
            },
            {
                "date": datetime(2024, 1, 20),
                "close": MoneyAmount(currency=Currency.RUB, value=Decimal("1010.00")),
            },
            {
                "date": datetime(2024, 1, 30),
                "close": MoneyAmount(currency=Currency.RUB, value=Decimal("1020.00")),
            },
        ],
    }
    service.get_historical_data = AsyncMock(return_value=historical_data)
    
    return service


@pytest.fixture
def tools(mock_portfolio_service):
    """Create instances of all portfolio tools."""
    return {
        "info": PortfolioInfoTool(mock_portfolio_service),
        "performance": PortfolioPerformanceTool(mock_portfolio_service),
        "pnl": PortfolioPnLTool(mock_portfolio_service),
        "cash_flow": PortfolioCashFlowTool(mock_portfolio_service),
    }


@pytest.mark.asyncio
async def test_portfolio_overview(tools, mock_portfolio_service):
    """Test getting a complete portfolio overview using all tools."""
    # Get portfolio info
    info_message = Message(
        content="Get portfolio info",
        metadata={"account_id": "test_account"}
    )
    info_result = await tools["info"].execute(info_message, {})
    
    assert info_result["account_id"] == "test_account"
    assert len(info_result["positions"]) == 2
    
    # Get portfolio performance
    performance_message = Message(
        content="Get portfolio performance",
        metadata={
            "account_id": "test_account",
            "period": "month",
        }
    )
    performance_result = await tools["performance"].execute(performance_message, {})
    
    assert performance_result["account_id"] == "test_account"
    assert "metrics" in performance_result
    assert "historical_data" in performance_result
    
    # Get portfolio PnL
    pnl_message = Message(
        content="Get portfolio PnL",
        metadata={
            "account_id": "test_account",
            "period": "month",
        }
    )
    pnl_result = await tools["pnl"].execute(pnl_message, {})
    
    assert pnl_result["account_id"] == "test_account"
    assert "total_pnl" in pnl_result
    assert len(pnl_result["operations"]) == 5
    
    # Get cash flows
    cash_flow_message = Message(
        content="Get cash flows",
        metadata={
            "account_id": "test_account",
            "period": "month",
        }
    )
    cash_flow_result = await tools["cash_flow"].execute(cash_flow_message, {})
    
    assert cash_flow_result["account_id"] == "test_account"
    assert "totals" in cash_flow_result
    assert len(cash_flow_result["flows"]) == 3


@pytest.mark.asyncio
async def test_portfolio_by_instrument_type(tools):
    """Test filtering portfolio data by instrument type."""
    instrument_type = "stock"
    
    # Get filtered info
    info_message = Message(
        content="Get portfolio info",
        metadata={
            "account_id": "test_account",
            "instrument_type": instrument_type,
        }
    )
    info_result = await tools["info"].execute(info_message, {})
    
    assert len(info_result["positions"]) == 1
    assert info_result["positions"][0]["type"] == instrument_type
    
    # Get filtered PnL
    pnl_message = Message(
        content="Get portfolio PnL",
        metadata={
            "account_id": "test_account",
            "instrument_type": instrument_type,
        }
    )
    pnl_result = await tools["pnl"].execute(pnl_message, {})
    
    assert all(op["instrument_type"] == InstrumentType.STOCK for op in pnl_result["operations"])
    
    # Get filtered cash flows
    cash_flow_message = Message(
        content="Get cash flows",
        metadata={
            "account_id": "test_account",
            "instrument_type": instrument_type,
        }
    )
    cash_flow_result = await tools["cash_flow"].execute(cash_flow_message, {})
    
    assert all(f["instrument_type"] == "stock" for f in cash_flow_result["flows"])


@pytest.mark.asyncio
async def test_portfolio_by_currency(tools):
    """Test filtering portfolio data by currency."""
    currency = "USD"
    
    # Get PnL in USD
    pnl_message = Message(
        content="Get portfolio PnL",
        metadata={
            "account_id": "test_account",
            "currency": currency,
        }
    )
    pnl_result = await tools["pnl"].execute(pnl_message, {})
    
    assert pnl_result["currency"] == currency
    
    # Get cash flows in USD
    cash_flow_message = Message(
        content="Get cash flows",
        metadata={
            "account_id": "test_account",
            "currency": currency,
        }
    )
    cash_flow_result = await tools["cash_flow"].execute(cash_flow_message, {})
    
    assert cash_flow_result["currency"] == currency


@pytest.mark.asyncio
async def test_portfolio_by_period(tools):
    """Test filtering portfolio data by period."""
    period = "month"
    
    # Get performance for period
    performance_message = Message(
        content="Get portfolio performance",
        metadata={
            "account_id": "test_account",
            "period": period,
        }
    )
    performance_result = await tools["performance"].execute(performance_message, {})
    
    assert performance_result["period"] == period
    
    # Get PnL for period
    pnl_message = Message(
        content="Get portfolio PnL",
        metadata={
            "account_id": "test_account",
            "period": period,
        }
    )
    pnl_result = await tools["pnl"].execute(pnl_message, {})
    
    assert pnl_result["period"] == period
    
    # Get cash flows for period
    cash_flow_message = Message(
        content="Get cash flows",
        metadata={
            "account_id": "test_account",
            "period": period,
        }
    )
    cash_flow_result = await tools["cash_flow"].execute(cash_flow_message, {})
    
    assert cash_flow_result["period"] == period


@pytest.mark.asyncio
async def test_portfolio_error_handling(tools):
    """Test error handling across all tools."""
    # Test with invalid account
    message = Message(
        content="Get portfolio info",
        metadata={"account_id": "invalid_account"}
    )
    
    for tool_name, tool in tools.items():
        result = await tool.execute(message, {})
        assert "error" in result
    
    # Test with invalid instrument type
    message = Message(
        content="Get portfolio info",
        metadata={
            "account_id": "test_account",
            "instrument_type": "invalid",
        }
    )
    
    for tool_name, tool in tools.items():
        result = await tool.execute(message, {})
        assert "error" in result
    
    # Test with invalid currency
    message = Message(
        content="Get portfolio info",
        metadata={
            "account_id": "test_account",
            "currency": "INVALID",
        }
    )
    
    for tool_name, tool in tools.items():
        if hasattr(tool, "currency"):
            result = await tool.execute(message, {})
            assert "error" in result
    
    # Test with invalid period
    message = Message(
        content="Get portfolio info",
        metadata={
            "account_id": "test_account",
            "period": "invalid",
        }
    )
    
    for tool_name, tool in tools.items():
        if hasattr(tool, "period"):
            result = await tool.execute(message, {})
            assert "error" in result 