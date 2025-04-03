"""
Portfolio PnL (Profit and Loss) tool for MCP agent.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
import logging

from src.agent.tools.base import BaseTool
from src.models.base import Message, Tool, ToolType
from src.services.tinkoff.models import Currency, InstrumentType, MoneyAmount, Position, OperationType
from src.services.tinkoff.portfolio import PortfolioService

logger = logging.getLogger(__name__)

class PortfolioPnLTool(BaseTool):
    """Tool for getting portfolio PnL information."""
    
    def __init__(self, portfolio_service: PortfolioService):
        """Initialize the tool with portfolio service."""
        self.portfolio_service = portfolio_service
        logger.info("Initialized PortfolioPnLTool")
        
        super().__init__(Tool(
            name="portfolio_pnl",
            type=ToolType.PORTFOLIO,
            description="Get profit and loss information for the portfolio",
            parameters={
                "account_id": {
                    "type": "string",
                    "description": "Portfolio account ID",
                    "required": False,
                },
                "instrument_type": {
                    "type": "string",
                    "description": "Filter PnL by instrument type (STOCK, BOND, ETF, etc.)",
                    "required": False,
                },
                "currency": {
                    "type": "string",
                    "description": "Currency to calculate PnL in (RUB, USD, EUR, etc.)",
                    "required": False,
                    "default": "RUB",
                },
                "period": {
                    "type": "string",
                    "description": "Time period for PnL calculation (day, week, month, year, all)",
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

    async def _calculate_position_pnl(
        self, position: Position, target_currency: Currency
    ) -> Dict[str, Any]:
        """Calculate PnL for a single position."""
        # Convert amounts to target currency if needed
        current_value = position.current_value
        if current_value.currency != target_currency:
            # TODO: Implement currency conversion
            pass
        
        # Calculate invested value
        invested_value = MoneyAmount(
            currency=position.average_price.currency,
            value=position.average_price.value * position.quantity
        )
        if invested_value.currency != target_currency:
            # TODO: Implement currency conversion
            pass
        
        # Calculate absolute and relative PnL
        absolute_pnl = MoneyAmount(
            currency=current_value.currency,
            value=current_value.value - invested_value.value
        )
        relative_pnl = (absolute_pnl.value / invested_value.value) * 100
        
        return {
            "figi": position.figi,
            "type": position.instrument_type.value,
            "quantity": str(position.quantity),
            "invested": {
                "value": str(invested_value.value),
                "currency": invested_value.currency.value,
            },
            "current": {
                "value": str(current_value.value),
                "currency": current_value.currency.value,
            },
            "pnl": {
                "absolute": {
                    "value": str(absolute_pnl.value),
                    "currency": absolute_pnl.currency.value,
                },
                "relative": str(relative_pnl),
            },
        }

    def _format_operation(self, op: Dict[str, Any]) -> Dict[str, Any]:
        """Format operation data for output."""
        formatted = {
            "date": op["date"].strftime("%Y-%m-%d") if op["date"] else None,
            "type": op["type"],
            "instrument_type": op["instrument_type"],
            "figi": op["figi"],
            "payment": {
                "value": str(op["payment"]),
                "currency": op["currency"]
            }
        }
        
        if op.get("commission"):
            formatted["commission"] = {
                "value": str(op["commission"]),
                "currency": op["currency"]
            }
            
        if op.get("tax"):
            formatted["tax"] = {
                "value": str(op["tax"]),
                "currency": op["currency"]
            }
            
        return formatted

    async def execute(self, message: Message, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool."""
        params = self.extract_parameters(message)
        account_id = params.get("account_id")
        instrument_type = params.get("instrument_type")
        currency = params.get("currency", Currency.USD)
        period = params.get("period", "1m")

        # Check if account exists
        accounts = await self.portfolio_service.get_accounts()
        if account_id not in accounts:
            logger.warning("Account %s not found", account_id)
            return {"error": f"Account {account_id} not found"}

        # Validate instrument type
        if instrument_type:
            try:
                instrument_type = InstrumentType(instrument_type.lower())
            except ValueError:
                return {"error": f"Invalid instrument type: {instrument_type}"}

        # Get period start date
        period_start = self._get_period_start(period) if period else None

        try:
            # Get operations
            operations = await self.portfolio_service.get_operations(
                account_id,
                from_date=period_start,
                to_date=datetime.now()
            )

            # Filter by instrument type if specified
            if instrument_type:
                operations = [op for op in operations if op["instrument_type"] == instrument_type]

            # Calculate total PnL
            total_pnl = Decimal("0")
            for op in operations:
                if op["type"] == "DIVIDEND":
                    total_pnl += Decimal(str(op["payment"])) - Decimal(str(op.get("tax", "0")))
                elif op["type"] == "COUPON":
                    total_pnl += Decimal(str(op["payment"])) - Decimal(str(op.get("tax", "0")))
                elif op["type"] == "SELL":
                    total_pnl += Decimal(str(op["payment"])) - Decimal(str(op.get("commission", "0")))

            result = {
                "account_id": account_id,
                "period": period,
                "currency": currency,
                "total_pnl": str(total_pnl),
                "operations": [
                    self._format_operation(op)
                    for op in operations
                ]
            }

            if instrument_type:
                result["instrument_type"] = instrument_type

            return result

        except Exception as e:
            logger.error("Error calculating PnL: %s", str(e))
            return {"error": str(e)} 