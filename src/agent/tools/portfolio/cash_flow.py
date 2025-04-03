"""
Portfolio cash flow tool for MCP agent.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
import logging

from src.agent.tools.base import BaseTool
from src.models.base import Message, Tool, ToolType
from src.services.tinkoff.models import Currency, InstrumentType, MoneyAmount
from src.services.tinkoff.portfolio import PortfolioService
from src.services.tinkoff.models import OperationType

logger = logging.getLogger(__name__)

class PortfolioCashFlowTool(BaseTool):
    """Tool for getting portfolio cash flow information."""
    
    def __init__(self, portfolio_service: PortfolioService):
        """Initialize the tool with portfolio service."""
        self.portfolio_service = portfolio_service
        logger.info("Initialized PortfolioCashFlowTool")
        
        super().__init__(Tool(
            name="portfolio_cash_flow",
            type=ToolType.PORTFOLIO,
            description="Get cash flow information for the portfolio",
            parameters={
                "account_id": {
                    "type": "string",
                    "description": "Portfolio account ID",
                    "required": False,
                },
                "instrument_type": {
                    "type": "string",
                    "description": "Filter cash flows by instrument type (STOCK, BOND, ETF, etc.)",
                    "required": False,
                },
                "currency": {
                    "type": "string",
                    "description": "Currency to calculate cash flows in (RUB, USD, EUR, etc.)",
                    "required": False,
                    "default": "RUB",
                },
                "period": {
                    "type": "string",
                    "description": "Time period for cash flow calculation (day, week, month, year, all)",
                    "required": False,
                    "default": "all",
                },
                "flow_type": {
                    "type": "string",
                    "description": "Type of cash flow (dividend, coupon, trade, tax, commission, all)",
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

    def _validate_flow_type(self, flow_type: str) -> None:
        """Validate cash flow type."""
        valid_types = {"dividend", "coupon", "trade", "tax", "commission", "all"}
        if flow_type not in valid_types:
            raise ValueError(f"Invalid flow type: {flow_type}")

    async def _get_cash_flows(
        self,
        account_id: str,
        period_start: Optional[datetime],
        target_currency: Currency,
        instrument_type: Optional[InstrumentType] = None,
        flow_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get cash flows for the given parameters."""
        operations = await self.portfolio_service.get_operations(
            account_id,
            from_date=period_start,
            to_date=datetime.now()
        )
        
        # Filter by instrument type if specified
        if instrument_type:
            operations = [op for op in operations if op["instrument_type"] == instrument_type]
            
        flows = []
        for op in operations:
            flow_data = {
                "date": op["date"],
                "instrument_id": op["figi"],
                "instrument_type": op["instrument_type"],
                "currency": op.get("currency", "RUB"),
                "amount": op["payment"],
            }
            
            if op["type"] in ["DIVIDEND", "COUPON"]:
                flow_data.update({
                    "type": op["type"].lower(),
                    "tax": op.get("tax", 0)
                })
                flows.append(flow_data)
            elif op["type"] == "SELL":  # Only include SELL operations, not BUY
                flow_data.update({
                    "type": "trade",
                    "commission": op.get("commission", 0)
                })
                flows.append(flow_data)
                
        # Filter by flow type if specified
        if flow_type and flow_type != "all":
            flows = [f for f in flows if f["type"] == flow_type]
            
        return flows

    def _format_flow(self, flow: Dict[str, Any]) -> Dict[str, Any]:
        """Format cash flow data for output."""
        formatted = {
            "date": flow["date"].strftime("%Y-%m-%d") if flow["date"] else None,
            "type": flow["type"],
            "instrument_type": flow["instrument_type"],
            "instrument_id": flow["instrument_id"],
            "amount": {
                "value": str(flow["amount"]),
                "currency": flow["currency"]
            }
        }
        
        if flow.get("commission"):
            formatted["commission"] = {
                "value": str(flow["commission"]),
                "currency": flow["currency"]
            }
            
        if flow.get("tax"):
            formatted["tax"] = {
                "value": str(flow["tax"]),
                "currency": flow["currency"]
            }
            
        return formatted

    async def execute(self, message: Message, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool."""
        params = self.extract_parameters(message)
        account_id = params.get("account_id")
        instrument_type = params.get("instrument_type")
        currency = params.get("currency", Currency.USD)
        period = params.get("period", "1m")
        flow_type = params.get("flow_type", "all")

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

        # Validate flow type
        if flow_type != "all" and not self._validate_flow_type(flow_type):
            return {"error": f"Invalid flow type: {flow_type}"}

        # Get cash flows
        flows = await self._get_cash_flows(
            account_id,
            period_start,
            currency,
            instrument_type,
            flow_type if flow_type != "all" else None
        )

        # Calculate totals
        total_amount = Decimal("0")
        total_commission = Decimal("0")
        total_tax = Decimal("0")

        for flow in flows:
            total_amount += flow["amount"]
            total_commission += flow.get("commission", Decimal("0"))
            total_tax += flow.get("tax", Decimal("0"))

        result = {
            "flows": flows,
            "totals": {
                "amount": total_amount,
                "commission": total_commission,
                "tax": total_tax,
                "currency": currency
            },
            "period": period,
            "account_id": account_id,
            "currency": currency
        }

        if instrument_type:
            result["instrument_type"] = instrument_type

        return result 