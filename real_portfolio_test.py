"""
Real portfolio analysis using MCP Agent with Tinkoff API.
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal

from src.models.base import Message
from src.services.tinkoff.client import TinkoffClient
from src.services.tinkoff.portfolio import PortfolioService
from src.agent.tools.portfolio.info import PortfolioInfoTool
from src.agent.tools.portfolio.performance import PortfolioPerformanceTool
from src.agent.tools.portfolio.pnl import PortfolioPnLTool
from src.agent.tools.portfolio.cash_flow import PortfolioCashFlowTool
from config import TINKOFF_TOKEN, DEFAULT_CURRENCY, DEFAULT_PERIOD

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def analyze_portfolio(account_id: str = None):
    """Analyze portfolio using real Tinkoff API data."""
    try:
        # Initialize Tinkoff client and services
        client = TinkoffClient(TINKOFF_TOKEN)
        portfolio_service = PortfolioService(client)
        
        # Initialize tools
        info_tool = PortfolioInfoTool(portfolio_service)
        performance_tool = PortfolioPerformanceTool(portfolio_service)
        pnl_tool = PortfolioPnLTool(portfolio_service)
        cash_flow_tool = PortfolioCashFlowTool(portfolio_service)
        
        # Get available accounts if account_id not provided
        if not account_id:
            accounts = await portfolio_service.get_accounts()
            if not accounts:
                logger.error("No accounts found")
                return
            account_id = accounts[0]
            logger.info(f"Using account: {account_id}")
            
        # 1. Portfolio Overview
        logger.info("Getting portfolio overview...")
        info_message = Message(
            content="Get portfolio info",
            metadata={"account_id": account_id}
        )
        info_result = await info_tool.execute(info_message, {})
        
        print("\n=== Portfolio Overview ===")
        print(f"Account ID: {info_result['account_id']}")
        print(f"Total positions: {len(info_result['positions'])}")
        
        # Group positions by type
        positions_by_type = {}
        total_value = Decimal("0")
        
        for pos in info_result["positions"]:
            pos_type = pos["instrument_type"]
            if pos_type not in positions_by_type:
                positions_by_type[pos_type] = []
            positions_by_type[pos_type].append(pos)
            
            # Calculate total value in account currency
            value = Decimal(str(pos["current_nkd"])) if "current_nkd" in pos else Decimal("0")
            value += Decimal(str(pos["current_price"])) * Decimal(str(pos["quantity"]))
            total_value += value
        
        # Print positions grouped by type
        for pos_type, positions in positions_by_type.items():
            print(f"\n{pos_type.upper()} positions:")
            for pos in positions:
                quantity = Decimal(str(pos["quantity"]))
                price = Decimal(str(pos["current_price"]))
                value = price * quantity
                if "current_nkd" in pos:
                    value += Decimal(str(pos["current_nkd"]))
                
                print(f"- {pos.get('name', pos['figi'])}: {quantity} units at {price} {pos.get('currency', 'RUB')}")
                print(f"  Current value: {value} {pos.get('currency', 'RUB')}")
                if "expected_yield" in pos:
                    print(f"  Expected yield: {pos['expected_yield']} {pos.get('currency', 'RUB')}")
        
        print(f"\nTotal portfolio value: {total_value} {DEFAULT_CURRENCY}")
        
        # 2. Performance Analysis
        logger.info("Getting performance metrics...")
        performance_message = Message(
            content="Get portfolio performance",
            metadata={
                "account_id": account_id,
                "period": DEFAULT_PERIOD,
                "currency": DEFAULT_CURRENCY
            }
        )
        performance_result = await performance_tool.execute(performance_message, {})
        
        print("\n=== Portfolio Performance ===")
        print(f"Period: {DEFAULT_PERIOD}")
        
        if "error" in performance_result:
            print("Error:", performance_result["error"])
        else:
            print("Total value:", performance_result["total_value"]["value"], performance_result["total_value"]["currency"])
            print("Total invested:", performance_result["total_invested"]["value"], performance_result["total_invested"]["currency"])
            print("Total yield:", performance_result["total_yield"]["absolute"]["value"], performance_result["total_yield"]["absolute"]["currency"])
            print("Relative yield:", performance_result["total_yield"]["relative"], "%")
        
        # 3. PnL Analysis
        logger.info("Getting PnL information...")
        pnl_message = Message(
            content="Get portfolio PnL",
            metadata={
                "account_id": account_id,
                "period": "month",
                "currency": "USD"
            }
        )
        pnl_result = await pnl_tool.execute(pnl_message, {})
        
        print("\n=== Portfolio PnL ===")
        print(f"Period: {pnl_result['period']}")
        print(f"Total PnL: {pnl_result['total_pnl']} {pnl_result['currency']}\n")
        
        print("Operations:")
        for op in pnl_result["operations"]:
            print(f"- {op['date']} {op['type']}: {op['payment']['value']} {op['payment']['currency']}")
            if op.get("commission"):
                print(f"  Commission: {op['commission']['value']} {op['commission']['currency']}")
            if op.get("tax"):
                print(f"  Tax: {op['tax']['value']} {op['tax']['currency']}")
        
        # 4. Cash Flow Analysis
        logger.info("Getting cash flow information...")
        cash_flow_message = Message(
            content="Get cash flows",
            metadata={
                "account_id": account_id,
                "period": DEFAULT_PERIOD,
                "currency": DEFAULT_CURRENCY
            }
        )
        cash_flow_result = await cash_flow_tool.execute(cash_flow_message, {})
        
        print("\n=== Portfolio Cash Flow ===")
        print(f"Period: {DEFAULT_PERIOD}")
        
        if "error" in cash_flow_result:
            print("Error:", cash_flow_result["error"])
        else:
            print("\nCash Flows:")
            for flow in cash_flow_result["flows"]:
                print(f"- {flow['date']} {flow['type'].upper()}: {flow['amount']['value']} {flow['amount']['currency']}")
                if "tax" in flow:
                    print(f"  Tax: {flow['tax']['value']} {flow['tax']['currency']}")
                if "commission" in flow:
                    print(f"  Commission: {flow['commission']['value']} {flow['commission']['currency']}")
        
        print("\nTotals:")
        print(f"Total amount: {cash_flow_result['totals']['amount']}")
        print(f"Total commission: {cash_flow_result['totals']['commission']}")
        print(f"Total tax: {cash_flow_result['totals']['tax']}")
        
    except Exception as e:
        logger.error(f"Error analyzing portfolio: {str(e)}")
        raise

async def main():
    """Main function."""
    print("MCP Agent - Portfolio Analysis")
    print("=" * 50)
    
    # You can specify account_id here if you have multiple accounts
    await analyze_portfolio()

if __name__ == "__main__":
    asyncio.run(main()) 