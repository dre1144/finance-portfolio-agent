"""
Example usage of MCP Agent portfolio tools.
This script demonstrates how to use the portfolio tools as an end user.
"""

import asyncio
from datetime import datetime
from decimal import Decimal

from src.models.base import Message
from src.services.tinkoff.models import Currency, InstrumentType, MoneyAmount, Position, Operation, OperationType
from src.services.tinkoff.portfolio import PortfolioService
from src.agent.tools.portfolio.info import PortfolioInfoTool
from src.agent.tools.portfolio.performance import PortfolioPerformanceTool
from src.agent.tools.portfolio.pnl import PortfolioPnLTool
from src.agent.tools.portfolio.cash_flow import PortfolioCashFlowTool

class MockPortfolioService:
    """Mock service for demonstration purposes."""
    
    async def get_accounts(self):
        return ["demo_account"]
    
    async def get_positions(self, account_id):
        return [
            Position(
                figi="AAPL",
                instrument_type=InstrumentType.STOCK,
                quantity=Decimal("10"),
                average_price=MoneyAmount(currency=Currency.USD, value=Decimal("150.25")),
                current_price=MoneyAmount(currency=Currency.USD, value=Decimal("155.50")),
                current_value=MoneyAmount(currency=Currency.USD, value=Decimal("1555.00")),
                expected_yield=MoneyAmount(currency=Currency.USD, value=Decimal("52.50")),
            ),
            Position(
                figi="BOND1",
                instrument_type=InstrumentType.BOND,
                quantity=Decimal("5"),
                average_price=MoneyAmount(currency=Currency.USD, value=Decimal("1000.00")),
                current_price=MoneyAmount(currency=Currency.USD, value=Decimal("1020.00")),
                current_value=MoneyAmount(currency=Currency.USD, value=Decimal("5100.00")),
                expected_yield=MoneyAmount(currency=Currency.USD, value=Decimal("100.00")),
            ),
        ]
    
    async def get_operations(self, account_id, from_date=None):
        return [
            Operation(
                id="op1",
                account_id=account_id,
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
                account_id=account_id,
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
                account_id=account_id,
                type=OperationType.SELL,
                instrument_id="MSFT",
                instrument_type=InstrumentType.STOCK,
                date=datetime(2024, 1, 15),
                amount=Decimal("777.50"),
                currency=Currency.USD,
                commission=Decimal("7.50")
            ),
        ]

    async def get_historical_data(self, account_id):
        return {
            "AAPL": [
                {
                    "date": datetime(2024, 1, 1),
                    "close": MoneyAmount(currency=Currency.USD, value=Decimal("150.25")),
                },
                {
                    "date": datetime(2024, 1, 15),
                    "close": MoneyAmount(currency=Currency.USD, value=Decimal("155.50")),
                },
            ],
            "BOND1": [
                {
                    "date": datetime(2024, 1, 1),
                    "close": MoneyAmount(currency=Currency.USD, value=Decimal("1000.00")),
                },
                {
                    "date": datetime(2024, 1, 15),
                    "close": MoneyAmount(currency=Currency.USD, value=Decimal("1020.00")),
                },
            ],
        }

async def main():
    """Run example usage of portfolio tools."""
    # Initialize services and tools
    portfolio_service = MockPortfolioService()
    info_tool = PortfolioInfoTool(portfolio_service)
    performance_tool = PortfolioPerformanceTool(portfolio_service)
    pnl_tool = PortfolioPnLTool(portfolio_service)
    cash_flow_tool = PortfolioCashFlowTool(portfolio_service)
    
    # Example 1: Get portfolio overview
    print("\n=== Portfolio Overview ===")
    info_message = Message(
        content="Get portfolio info",
        metadata={"account_id": "demo_account"}
    )
    info_result = await info_tool.execute(info_message, {})
    print("Portfolio positions:", len(info_result["positions"]))
    for pos in info_result["positions"]:
        print(f"- {pos['type']}: {pos['quantity']} units at {pos['current_price']['value']} {pos['current_price']['currency']}")
    
    # Example 2: Get performance metrics
    print("\n=== Portfolio Performance ===")
    performance_message = Message(
        content="Get portfolio performance",
        metadata={
            "account_id": "demo_account",
            "period": "month",
            "currency": "USD"
        }
    )
    performance_result = await performance_tool.execute(performance_message, {})
    print("Total value:", performance_result["metrics"]["total_value"])
    print("Total yield:", performance_result["metrics"]["total_yield"])
    
    # Example 3: Get PnL information
    print("\n=== Portfolio PnL ===")
    pnl_message = Message(
        content="Get portfolio PnL",
        metadata={
            "account_id": "demo_account",
            "period": "month",
            "currency": "USD"
        }
    )
    pnl_result = await pnl_tool.execute(pnl_message, {})
    print("Total PnL:", pnl_result["total_pnl"], pnl_result["currency"])
    print("Number of operations:", len(pnl_result["operations"]))
    
    # Example 4: Get cash flows
    print("\n=== Portfolio Cash Flows ===")
    cash_flow_message = Message(
        content="Get cash flows",
        metadata={
            "account_id": "demo_account",
            "period": "month",
            "currency": "USD"
        }
    )
    cash_flow_result = await cash_flow_tool.execute(cash_flow_message, {})
    print("Number of cash flows:", len(cash_flow_result["flows"]))
    print("Total amount:", cash_flow_result["totals"]["amount"])
    print("Total commission:", cash_flow_result["totals"]["commission"])
    print("Total tax:", cash_flow_result["totals"]["tax"])
    
    # Example 5: Filter by instrument type
    print("\n=== Stock-only Portfolio Info ===")
    stock_message = Message(
        content="Get portfolio info",
        metadata={
            "account_id": "demo_account",
            "instrument_type": "stock"
        }
    )
    stock_result = await info_tool.execute(stock_message, {})
    print("Number of stock positions:", len(stock_result["positions"]))

if __name__ == "__main__":
    asyncio.run(main()) 