"""
Tests for Tinkoff API portfolio service.
"""

from datetime import datetime
from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, patch

from src.services.tinkoff.client import TinkoffClient
from src.services.tinkoff.models import Currency, InstrumentType, MoneyAmount, Position
from src.services.tinkoff.portfolio import PortfolioService


@pytest.fixture
def client():
    """Create test client instance."""
    return TinkoffClient("test_token")


@pytest.fixture
def service(client):
    """Create test portfolio service instance."""
    return PortfolioService(client)


@pytest.fixture
def mock_portfolio_response():
    """Create mock portfolio response."""
    return {
        "totalAmountPortfolio": {
            "currency": "RUB",
            "units": "100000",
        },
        "expectedYield": {
            "currency": "RUB",
            "units": "5000",
        },
        "positions": [
            {
                "figi": "BBG000B9XRY4",
                "instrumentType": "STOCK",
                "quantity": {
                    "units": "10",
                },
                "averagePositionPrice": {
                    "currency": "USD",
                    "units": "150.25",
                },
                "currentPrice": {
                    "currency": "USD",
                    "units": "155.50",
                },
                "currentValue": {
                    "currency": "USD",
                    "units": "1555.00",
                },
                "expectedYield": {
                    "currency": "USD",
                    "units": "52.50",
                },
            },
        ],
    }


@pytest.fixture
def mock_currencies_response():
    """Create mock currencies response."""
    return {
        "currencies": [
            {
                "currency": "RUB",
                "balance": {
                    "units": "50000",
                },
            },
            {
                "currency": "USD",
                "balance": {
                    "units": "1000",
                },
            },
            {
                "currency": "EUR",
                "balance": {
                    "units": "0",
                },
            },
        ],
    }


@pytest.mark.asyncio
async def test_get_accounts(service):
    """Test getting user accounts."""
    with patch.object(service.client, "get") as mock_get:
        mock_get.return_value = {
            "accounts": [
                {"brokerAccountId": "123"},
                {"brokerAccountId": "456"},
            ],
        }
        
        accounts = await service.get_accounts()
        assert accounts == ["123", "456"]
        mock_get.assert_called_once_with("/user/accounts")


@pytest.mark.asyncio
async def test_get_portfolio(service, mock_portfolio_response, mock_currencies_response):
    """Test getting portfolio information."""
    with patch.object(service.client, "get") as mock_get:
        mock_get.side_effect = [
            mock_portfolio_response,
            mock_currencies_response,
        ]
        
        portfolio = await service.get_portfolio("123")
        
        assert portfolio.account_id == "123"
        assert portfolio.total_amount.currency == Currency.RUB
        assert portfolio.total_amount.value == Decimal("100000")
        assert portfolio.expected_yield.value == Decimal("5000")
        
        assert len(portfolio.positions) == 1
        position = portfolio.positions[0]
        assert position.figi == "BBG000B9XRY4"
        assert position.instrument_type == InstrumentType.STOCK
        assert position.quantity == Decimal("10")
        assert position.average_price.value == Decimal("150.25")
        
        assert len(portfolio.cash) == 2
        assert any(c.currency == Currency.RUB and c.value == Decimal("50000") for c in portfolio.cash)
        assert any(c.currency == Currency.USD and c.value == Decimal("1000") for c in portfolio.cash)


@pytest.mark.asyncio
async def test_get_position(service, mock_portfolio_response, mock_currencies_response):
    """Test getting specific position."""
    with patch.object(service.client, "get") as mock_get:
        mock_get.side_effect = [
            mock_portfolio_response,
            mock_currencies_response,
        ]
        
        # Existing position
        position = await service.get_position("123", "BBG000B9XRY4")
        assert position is not None
        assert position.figi == "BBG000B9XRY4"
        assert position.quantity == Decimal("10")
        
        # Non-existing position
        position = await service.get_position("123", "INVALID")
        assert position is None


@pytest.mark.asyncio
async def test_get_positions_by_type(service, mock_portfolio_response, mock_currencies_response):
    """Test getting positions by type."""
    with patch.object(service.client, "get") as mock_get:
        mock_get.side_effect = [
            mock_portfolio_response,
            mock_currencies_response,
        ]
        
        # Existing type
        positions = await service.get_positions_by_type("123", InstrumentType.STOCK)
        assert len(positions) == 1
        assert positions[0].figi == "BBG000B9XRY4"
        
        # Non-existing type
        positions = await service.get_positions_by_type("123", InstrumentType.BOND)
        assert len(positions) == 0


@pytest.mark.asyncio
async def test_get_cash_by_currency(service, mock_portfolio_response, mock_currencies_response):
    """Test getting cash by currency."""
    with patch.object(service.client, "get") as mock_get:
        mock_get.side_effect = [
            mock_portfolio_response,
            mock_currencies_response,
        ]
        
        # Existing currency
        amount = await service.get_cash_by_currency("123", Currency.RUB)
        assert amount is not None
        assert amount.currency == Currency.RUB
        assert amount.value == Decimal("50000")
        
        # Non-existing currency
        amount = await service.get_cash_by_currency("123", Currency.EUR)
        assert amount is None 