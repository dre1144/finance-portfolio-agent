"""
Portfolio information tool for MCP agent.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from decimal import Decimal

from src.agent.tools.base import BaseTool
from src.models.base import Message, Tool, ToolType
from src.services.tinkoff.models import Currency, InstrumentType, Portfolio, Position, MoneyAmount
from src.services.tinkoff.portfolio import PortfolioService

logger = logging.getLogger(__name__)

class PortfolioInfoTool(BaseTool):
    """Tool for getting portfolio information."""
    
    def __init__(self, portfolio_service: PortfolioService):
        """Initialize the tool with portfolio service."""
        self.portfolio_service = portfolio_service
        logger.info("Initialized PortfolioInfoTool")
        
        super().__init__(Tool(
            name="portfolio_info",
            type=ToolType.PORTFOLIO,
            description="Get portfolio information",
            parameters={
                "account_id": {
                    "type": "string",
                    "description": "Portfolio account ID",
                    "required": False,
                },
                "instrument_type": {
                    "type": "string",
                    "description": "Filter positions by instrument type (STOCK, BOND, ETF, etc.)",
                    "required": False,
                },
            },
            required_parameters=[],
        ))

    def extract_parameters(self, message: Message) -> Dict[str, Any]:
        """Extract tool parameters from message.
        
        Args:
            message: Message to extract parameters from
            
        Returns:
            Dictionary of extracted parameters
        """
        params = {}
        
        # Extract parameters from message metadata if available
        if message.metadata:
            params = {
                key: value
                for key, value in message.metadata.items()
                if key in self.config.parameters
            }
        
        return params

    def _format_position(self, position: Position) -> Dict[str, Any]:
        """Format position data for output."""
        return {
            "figi": position.figi,
            "type": position.instrument_type.value,
            "quantity": str(position.quantity),
            "average_price": {
                "value": str(position.average_price.value),
                "currency": position.average_price.currency.value,
            },
            "current_price": {
                "value": str(position.current_price.value),
                "currency": position.current_price.currency.value,
            },
            "current_value": {
                "value": str(position.current_value.value),
                "currency": position.current_value.currency.value,
            },
            "expected_yield": {
                "value": str(position.expected_yield.value),
                "currency": position.expected_yield.currency.value,
            },
        }

    async def _format_portfolio(self, portfolio: Portfolio) -> Dict[str, Any]:
        """Format portfolio data for output."""
        return {
            "account_id": portfolio.account_id,
            "total_amount": {
                "value": str(portfolio.total_amount.value),
                "currency": portfolio.total_amount.currency.value,
            },
            "expected_yield": {
                "value": str(portfolio.expected_yield.value),
                "currency": portfolio.expected_yield.currency.value,
            },
            "positions": [
                await self._format_position(pos) for pos in portfolio.positions
            ],
            "cash": [
                {
                    "value": str(cash.value),
                    "currency": cash.currency.value,
                }
                for cash in portfolio.cash
            ],
            "updated_at": portfolio.updated_at.isoformat(),
        }

    async def execute(self, message: Message, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given message and context."""
        params = self.extract_parameters(message)
        
        account_id = params.get("account_id")
        instrument_type = params.get("instrument_type")
        
        # If no account ID provided, get the first available account
        if not account_id:
            accounts = await self.portfolio_service.get_accounts()
            if not accounts:
                logger.warning("No accounts found")
                return {"error": "No accounts found"}
            account_id = accounts[0]["id"]  # Get ID from account dict
            logger.info("Using first available account: %s", account_id)
        
        try:
            # Get portfolio
            portfolio = await self.portfolio_service.get_portfolio(account_id)
            if not portfolio or not portfolio.get("positions"):
                logger.warning("No positions found for account %s", account_id)
                return {"error": f"No positions found for account {account_id}"}
            
            positions = portfolio["positions"]
            
            # Filter positions by instrument type if needed
            if instrument_type:
                positions = [
                    pos for pos in positions
                    if pos["instrument_type"].lower() == instrument_type.lower()
                ]
                if not positions:
                    return {"error": f"No positions found for type {instrument_type}"}
            
            return {
                "account_id": account_id,
                "positions": positions
            }
            
        except Exception as e:
            logger.error("Failed to get portfolio info: %s", str(e))
            return {"error": f"Failed to get portfolio info: {str(e)}"}

    async def execute_with_instrument_type(self, account_id: Optional[str] = None, instrument_type: Optional[str] = None) -> Dict[str, Any]:
        logger.info("Executing PortfolioInfoTool with account_id: %s and instrument_type: %s", account_id, instrument_type)
        if not account_id:
            accounts = await self.portfolio_service.get_accounts()
            if not accounts:
                logger.warning("No accounts found")
                return {"error": "No accounts found"}
            account_id = accounts[0]
            logger.info("Using first available account: %s", account_id)
            
        if instrument_type:
            try:
                type_enum = InstrumentType(instrument_type.lower())
                positions = await self.portfolio_service.get_positions_by_type(account_id, type_enum)
                if not positions:
                    logger.warning("No positions found for type %s", instrument_type)
                    return {"error": f"No positions found for type {instrument_type}"}
                return {
                    "positions": [
                        await self._format_position(pos) for pos in positions
                    ]
                }
            except ValueError as e:
                logger.error("Invalid instrument type: %s", instrument_type)
                return {"error": f"Invalid instrument type: {instrument_type}"}

        portfolio = await self.portfolio_service.get_portfolio(account_id)
        logger.info("Got portfolio info for account %s", account_id)
        return await self._format_portfolio(portfolio)

    async def execute_with_currency(self, account_id: Optional[str] = None, currency: Optional[str] = None) -> Dict[str, Any]:
        logger.info("Executing PortfolioInfoTool with account_id: %s and currency: %s", account_id, currency)
        if not account_id:
            accounts = await self.portfolio_service.get_accounts()
            if not accounts:
                logger.warning("No accounts found")
                return {"error": "No accounts found"}
            account_id = accounts[0]
            logger.info("Using first available account: %s", account_id)
            
        if currency:
            try:
                currency_enum = Currency(currency.upper())
                amount = await self.portfolio_service.get_cash_by_currency(account_id, currency_enum)
                if not amount:
                    logger.warning("No cash found for currency %s", currency)
                    return {"error": f"No cash found for currency {currency}"}
                return {
                    "cash": {
                        "value": str(amount.value),
                        "currency": amount.currency.value,
                    }
                }
            except ValueError:
                logger.error("Invalid currency: %s", currency)
                return {"error": f"Invalid currency: {currency}"}

        portfolio = await self.portfolio_service.get_portfolio(account_id)
        logger.info("Got portfolio info for account %s", account_id)
        return await self._format_portfolio(portfolio) 