"""
Portfolio performance tool for MCP agent.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
import logging

from src.agent.tools.base import BaseTool
from src.models.base import Message, Tool, ToolType
from src.services.tinkoff.models import Currency, InstrumentType, MoneyAmount, Position
from src.services.tinkoff.portfolio import PortfolioService

logger = logging.getLogger(__name__)

class PortfolioPerformanceTool(BaseTool):
    """Tool for getting portfolio performance information."""
    
    def __init__(self, portfolio_service: PortfolioService):
        """Initialize the tool with portfolio service."""
        self.portfolio_service = portfolio_service
        logger.info("Initialized PortfolioPerformanceTool")
        
        super().__init__(Tool(
            name="portfolio_performance",
            type=ToolType.PORTFOLIO,
            description="Get performance metrics for the portfolio",
            parameters={
                "account_id": {
                    "type": "string",
                    "description": "Portfolio account ID",
                    "required": False,
                },
                "instrument_type": {
                    "type": "string",
                    "description": "Filter performance by instrument type (STOCK, BOND, ETF, etc.)",
                    "required": False,
                },
                "currency": {
                    "type": "string",
                    "description": "Currency to calculate performance in (RUB, USD, EUR, etc.)",
                    "required": False,
                    "default": "RUB",
                },
                "period": {
                    "type": "string",
                    "description": "Time period for performance calculation (day, week, month, year, all)",
                    "required": False,
                    "default": "all",
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
        
        # Set default values for missing parameters
        for name, param in self.config.parameters.items():
            if name not in params and "default" in param:
                params[name] = param["default"]
        
        return params

    def _get_period_start(self, period: str) -> Optional[datetime]:
        """Get start datetime for the given period."""
        now = datetime.now()
        
        if period == "day":
            return now - timedelta(days=1)
        elif period == "week":
            return now - timedelta(weeks=1)
        elif period == "month":
            return now - timedelta(days=30)
        elif period == "year":
            return now - timedelta(days=365)
        elif period == "all":
            return None
        else:
            raise ValueError(f"Invalid period: {period}")

    async def _calculate_metrics(
        self,
        positions: List[Dict[str, Any]],
        historical_data: Dict[str, List[Dict[str, Any]]],
        target_currency: Currency,
    ) -> Dict[str, Any]:
        """Calculate performance metrics."""
        total_value = Decimal("0")
        total_invested = Decimal("0")
        total_yield = Decimal("0")
        
        for pos in positions:
            # Calculate current value including NKD for bonds
            current_value = Decimal(str(pos["current_price"])) * Decimal(str(pos["quantity"]))
            if "current_nkd" in pos:
                current_value += Decimal(str(pos["current_nkd"]))
            
            # Calculate invested value
            invested_value = Decimal(str(pos["average_position_price"])) * Decimal(str(pos["quantity"]))
            if "aci_value" in pos:  # Add accrued interest for bonds
                invested_value += Decimal(str(pos["aci_value"]))
            
            # Get expected yield
            expected_yield = Decimal(str(pos.get("expected_yield", "0")))
            
            total_value += current_value
            total_invested += invested_value
            total_yield += expected_yield
        
        # Calculate relative metrics
        relative_yield = (total_yield / total_invested) * 100 if total_invested else Decimal("0")
        
        return {
            "total_value": {
                "value": str(total_value),
                "currency": target_currency.value,
            },
            "total_invested": {
                "value": str(total_invested),
                "currency": target_currency.value,
            },
            "total_yield": {
                "absolute": {
                    "value": str(total_yield),
                    "currency": target_currency.value,
                },
                "relative": str(relative_yield),
            },
        }

    async def execute(self, message: Message, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given message and context."""
        params = self.extract_parameters(message)
        
        account_id = params.get("account_id")
        instrument_type = params.get("instrument_type")
        currency = params.get("currency", "RUB")
        period = params.get("period", "all")
        
        # If no account ID provided, get the first available account
        if not account_id:
            accounts = await self.portfolio_service.get_accounts()
            if not accounts:
                logger.warning("No accounts found")
                return {"error": "No accounts found"}
            account_id = accounts[0]
            logger.info("Using first available account: %s", account_id)
        
        # Get period start date
        period_start = self._get_period_start(period)
        target_currency = Currency(currency.upper())
        
        try:
            # Check if account exists
            accounts = await self.portfolio_service.get_accounts()
            if account_id not in accounts:
                logger.warning("Account %s not found", account_id)
                return {"error": f"Account {account_id} not found"}

            # Get positions
            portfolio = await self.portfolio_service.get_portfolio(account_id)
            if not portfolio or not portfolio["positions"]:
                return {"error": f"No positions found for account {account_id}"}
            
            positions = portfolio["positions"]
            
            # Calculate metrics without historical data
            metrics = await self._calculate_metrics(positions, {}, target_currency)
            return metrics
        except Exception as e:
            logger.error("Error getting historical data: %s", e)
            return {"error": "Error getting historical data"}
        
        # Filter positions by instrument type if needed
        if instrument_type:
            try:
                instrument_type_enum = InstrumentType(instrument_type.lower())
                positions = [
                    pos for pos in positions
                    if pos.instrument_type == instrument_type_enum
                ]
                if not positions:
                    return {"error": f"No positions found for type {instrument_type}"}
            except ValueError:
                return {"error": f"Invalid instrument type: {instrument_type}"}
        
        # Calculate metrics
        metrics = await self._calculate_metrics(
            positions=positions,
            historical_data=historical_data,
            target_currency=target_currency,
        )
        
        return {
            "account_id": account_id,
            "currency": target_currency.value,
            "period": period,
            "metrics": metrics,
            "historical_data": historical_data,
        } 