"""
Portfolio service implementation for Tinkoff Invest.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from .client import TinkoffClient
from .models import Currency, InstrumentType, MoneyAmount, Position, Portfolio

logger = logging.getLogger(__name__)

class PortfolioService:
    """Service for working with portfolio data from Tinkoff Invest."""

    def __init__(self, client: TinkoffClient):
        """Initialize service with API client."""
        self.client = client
        logger.info("Initialized PortfolioService")

    async def get_accounts(self) -> List[Dict]:
        """Get list of user's brokerage accounts."""
        logger.info("Getting accounts")
        accounts = await self.client.get_accounts()
        logger.info("Found %d accounts", len(accounts))
        return accounts

    async def get_portfolio(self, account_id: str) -> Dict:
        """Get portfolio state for specified account."""
        logger.info("Getting portfolio for account %s", account_id)
        # If account_id is a dict, extract the ID
        if isinstance(account_id, dict):
            account_id = account_id["id"]
        portfolio = await self.client.get_portfolio(account_id)
        logger.info("Got portfolio with %d positions", len(portfolio["positions"]))
        return portfolio

    async def get_operations(
        self,
        account_id: Union[str, Dict[str, Any]],
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get operations for the account."""
        logger.info("Getting operations for account %s from %s to %s", account_id, from_date, to_date)
        
        # Extract account ID from dictionary if needed
        if isinstance(account_id, dict):
            account_id = account_id["id"]
        
        operations = await self.client.get_operations(
            account_id=account_id,
            from_date=from_date,
            to_date=to_date,
        )
        
        return operations

    async def get_position(self, account_id: str, figi: str) -> Optional[Position]:
        """
        Get specific position from portfolio.

        Args:
            account_id: Broker account ID
            figi: Instrument FIGI

        Returns:
            Position information or None if not found
        """
        portfolio = await self.get_portfolio(account_id)
        for position in portfolio.positions:
            if position.figi == figi:
                return position
        return None

    async def get_positions_by_type(
        self,
        account_id: str,
        instrument_type: InstrumentType,
    ) -> List[Position]:
        """
        Get all positions of specific type.

        Args:
            account_id: Broker account ID
            instrument_type: Type of instrument

        Returns:
            List of positions
        """
        portfolio = await self.get_portfolio(account_id)
        return [
            position for position in portfolio.positions
            if position.instrument_type == instrument_type
        ]

    async def get_cash_by_currency(
        self,
        account_id: str,
        currency: Currency,
    ) -> Optional[MoneyAmount]:
        """
        Get cash amount in specific currency.

        Args:
            account_id: Broker account ID
            currency: Currency code

        Returns:
            Money amount or None if no cash in specified currency
        """
        portfolio = await self.get_portfolio(account_id)
        for amount in portfolio.cash:
            if amount.currency == currency:
                return amount
        return None 