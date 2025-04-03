"""
Tests for Tinkoff API data models.
"""

from datetime import datetime
from decimal import Decimal
import pytest
from pydantic import ValidationError

from src.services.tinkoff.models import (
    Currency,
    InstrumentType,
    MoneyAmount,
    Instrument,
    Position,
    Portfolio,
)


def test_money_amount_creation():
    """Test MoneyAmount model creation."""
    amount = MoneyAmount(currency=Currency.RUB, value=Decimal("100.50"))
    assert amount.currency == Currency.RUB
    assert amount.value == Decimal("100.50")


def test_money_amount_addition():
    """Test MoneyAmount addition."""
    amount1 = MoneyAmount(currency=Currency.RUB, value=Decimal("100.50"))
    amount2 = MoneyAmount(currency=Currency.RUB, value=Decimal("50.25"))
    
    result = amount1 + amount2
    assert result.currency == Currency.RUB
    assert result.value == Decimal("150.75")


def test_money_amount_subtraction():
    """Test MoneyAmount subtraction."""
    amount1 = MoneyAmount(currency=Currency.RUB, value=Decimal("100.50"))
    amount2 = MoneyAmount(currency=Currency.RUB, value=Decimal("50.25"))
    
    result = amount1 - amount2
    assert result.currency == Currency.RUB
    assert result.value == Decimal("50.25")


def test_money_amount_different_currencies():
    """Test MoneyAmount operations with different currencies."""
    amount1 = MoneyAmount(currency=Currency.RUB, value=Decimal("100.50"))
    amount2 = MoneyAmount(currency=Currency.USD, value=Decimal("50.25"))
    
    with pytest.raises(ValueError):
        _ = amount1 + amount2
    
    with pytest.raises(ValueError):
        _ = amount1 - amount2


def test_instrument_creation():
    """Test Instrument model creation."""
    instrument = Instrument(
        figi="BBG000B9XRY4",
        ticker="AAPL",
        isin="US0378331005",
        name="Apple Inc",
        type=InstrumentType.STOCK,
        lot=1,
        currency=Currency.USD,
        min_price_increment=Decimal("0.01"),
    )
    
    assert instrument.figi == "BBG000B9XRY4"
    assert instrument.ticker == "AAPL"
    assert instrument.type == InstrumentType.STOCK
    assert instrument.currency == Currency.USD


def test_position_creation():
    """Test Position model creation."""
    position = Position(
        figi="BBG000B9XRY4",
        instrument_type=InstrumentType.STOCK,
        quantity=Decimal("10"),
        average_price=MoneyAmount(
            currency=Currency.USD,
            value=Decimal("150.25"),
        ),
        current_price=MoneyAmount(
            currency=Currency.USD,
            value=Decimal("155.50"),
        ),
        current_value=MoneyAmount(
            currency=Currency.USD,
            value=Decimal("1555.00"),
        ),
        expected_yield=MoneyAmount(
            currency=Currency.USD,
            value=Decimal("52.50"),
        ),
    )
    
    assert position.figi == "BBG000B9XRY4"
    assert position.quantity == Decimal("10")
    assert position.average_price.value == Decimal("150.25")
    assert position.current_price.value == Decimal("155.50")


def test_portfolio_creation():
    """Test Portfolio model creation."""
    portfolio = Portfolio(
        account_id="123456",
        total_amount=MoneyAmount(
            currency=Currency.RUB,
            value=Decimal("100000.00"),
        ),
        positions=[
            Position(
                figi="BBG000B9XRY4",
                instrument_type=InstrumentType.STOCK,
                quantity=Decimal("10"),
                average_price=MoneyAmount(
                    currency=Currency.USD,
                    value=Decimal("150.25"),
                ),
                current_price=MoneyAmount(
                    currency=Currency.USD,
                    value=Decimal("155.50"),
                ),
                current_value=MoneyAmount(
                    currency=Currency.USD,
                    value=Decimal("1555.00"),
                ),
                expected_yield=MoneyAmount(
                    currency=Currency.USD,
                    value=Decimal("52.50"),
                ),
            ),
        ],
        cash=[
            MoneyAmount(
                currency=Currency.RUB,
                value=Decimal("50000.00"),
            ),
            MoneyAmount(
                currency=Currency.USD,
                value=Decimal("1000.00"),
            ),
        ],
        expected_yield=MoneyAmount(
            currency=Currency.RUB,
            value=Decimal("5000.00"),
        ),
        updated_at=datetime.now(),
    )
    
    assert portfolio.account_id == "123456"
    assert portfolio.total_amount.value == Decimal("100000.00")
    assert len(portfolio.positions) == 1
    assert len(portfolio.cash) == 2
    assert portfolio.expected_yield.value == Decimal("5000.00")


def test_portfolio_validation():
    """Test Portfolio model validation."""
    with pytest.raises(ValidationError):
        # Missing required fields
        Portfolio()
    
    with pytest.raises(ValidationError):
        # Invalid currency
        Portfolio(
            account_id="123456",
            total_amount=MoneyAmount(
                currency="INVALID",  # type: ignore
                value=Decimal("100000.00"),
            ),
            updated_at=datetime.now(),
        )
    
    with pytest.raises(ValidationError):
        # Invalid instrument type
        Portfolio(
            account_id="123456",
            total_amount=MoneyAmount(
                currency=Currency.RUB,
                value=Decimal("100000.00"),
            ),
            positions=[
                Position(
                    figi="BBG000B9XRY4",
                    instrument_type="INVALID",  # type: ignore
                    quantity=Decimal("10"),
                    average_price=MoneyAmount(
                        currency=Currency.USD,
                        value=Decimal("150.25"),
                    ),
                ),
            ],
            updated_at=datetime.now(),
        ) 