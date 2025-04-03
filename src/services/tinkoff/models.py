"""
Data models for Tinkoff API responses.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Currency(str, Enum):
    """Currency codes."""
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    HKD = "HKD"
    CHF = "CHF"
    JPY = "JPY"
    CNY = "CNY"
    TRY = "TRY"


class InstrumentType(str, Enum):
    """Types of financial instruments."""
    STOCK = "stock"
    BOND = "bond"
    ETF = "etf"
    CURRENCY = "currency"
    FUTURES = "futures"


class OperationType(str, Enum):
    """Types of operations."""
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    COUPON = "coupon"
    TAX = "tax"
    COMMISSION = "commission"


class MoneyAmount(BaseModel):
    """Money amount with currency."""
    currency: Currency
    value: Decimal = Field(..., description="Amount in currency units")

    def __add__(self, other: "MoneyAmount") -> "MoneyAmount":
        if not isinstance(other, MoneyAmount):
            raise TypeError("Can only add MoneyAmount to MoneyAmount")
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return MoneyAmount(
            currency=self.currency,
            value=self.value + other.value,
        )

    def __sub__(self, other: "MoneyAmount") -> "MoneyAmount":
        if not isinstance(other, MoneyAmount):
            raise TypeError("Can only subtract MoneyAmount from MoneyAmount")
        if self.currency != other.currency:
            raise ValueError("Cannot subtract different currencies")
        return MoneyAmount(
            currency=self.currency,
            value=self.value - other.value,
        )


class Instrument(BaseModel):
    """Financial instrument."""
    figi: str = Field(..., description="FIGI identifier")
    ticker: str = Field(..., description="Ticker symbol")
    isin: Optional[str] = Field(None, description="ISIN code")
    name: str = Field(..., description="Instrument name")
    type: InstrumentType = Field(..., description="Instrument type")
    lot: int = Field(..., description="Lot size")
    currency: Currency = Field(..., description="Trading currency")
    min_price_increment: Optional[Decimal] = Field(None, description="Minimum price change")


class Position(BaseModel):
    """Portfolio position."""
    figi: str = Field(..., description="Instrument FIGI")
    instrument_type: InstrumentType = Field(..., description="Instrument type")
    quantity: Decimal = Field(..., description="Number of lots")
    average_price: MoneyAmount = Field(..., description="Average purchase price")
    current_price: Optional[MoneyAmount] = Field(None, description="Current market price")
    current_value: Optional[MoneyAmount] = Field(None, description="Current position value")
    expected_yield: Optional[MoneyAmount] = Field(None, description="Unrealized P&L")


class Portfolio(BaseModel):
    """Investment portfolio."""
    account_id: str = Field(..., description="Account identifier")
    total_amount: MoneyAmount = Field(..., description="Total portfolio value")
    positions: List[Position] = Field(default_factory=list, description="Portfolio positions")
    cash: List[MoneyAmount] = Field(default_factory=list, description="Available cash by currency")
    expected_yield: Optional[MoneyAmount] = Field(None, description="Total unrealized P&L")
    updated_at: datetime = Field(..., description="Last update timestamp")


class Operation(BaseModel):
    """Portfolio operation."""
    id: str = Field(..., description="Operation identifier")
    account_id: str = Field(..., description="Account identifier")
    type: OperationType = Field(..., description="Operation type")
    instrument_id: str = Field(..., description="Instrument identifier")
    instrument_type: InstrumentType = Field(..., description="Instrument type")
    date: datetime = Field(..., description="Operation date")
    amount: Decimal = Field(..., description="Operation amount")
    currency: Currency = Field(..., description="Operation currency")
    commission: Optional[Decimal] = Field(None, description="Commission amount")
    tax: Optional[Decimal] = Field(None, description="Tax amount") 