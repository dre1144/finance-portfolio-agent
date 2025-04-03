import asyncio
import os
from datetime import datetime, timedelta
from decimal import Decimal
from dotenv import load_dotenv

from src.services.tinkoff.client import TinkoffClient
from src.services.tinkoff.portfolio import PortfolioService
from src.agent.tools.portfolio.info import PortfolioInfoTool
from src.agent.tools.portfolio.pnl import PortfolioPnLTool
from src.agent.tools.portfolio.performance import PortfolioPerformanceTool
from src.agent.tools.portfolio.cash_flow import PortfolioCashFlowTool

# Load environment variables
load_dotenv()

async def main():
    # Initialize client with token from .env
    token = os.getenv("TINKOFF_TOKEN")
    if not token:
        raise ValueError("TINKOFF_TOKEN not found in environment variables")
    
    print("Initializing client with token:", token[:10] + "..." + token[-10:])
    client = TinkoffClient(token)
    portfolio_service = PortfolioService(client)
    
    # Initialize tools
    info_tool = PortfolioInfoTool(portfolio_service)
    pnl_tool = PortfolioPnLTool(portfolio_service)
    performance_tool = PortfolioPerformanceTool(portfolio_service)
    cash_flow_tool = PortfolioCashFlowTool(portfolio_service)
    
    try:
        # Get accounts
        accounts = await portfolio_service.get_accounts()
        print(f"\nFound {len(accounts)} account(s)")
        
        for account in accounts:
            print(f"\n=== Account {account} ===")
            
            # Get portfolio info
            print("\n--- Portfolio Info ---")
            info = await info_tool.execute(account_id=account)
            print(info)
            
            # Get PnL for last month
            print("\n--- PnL (Last Month) ---")
            start_date = datetime.now() - timedelta(days=30)
            pnl = await pnl_tool.execute(
                account_id=account,
                from_date=start_date
            )
            print(pnl)
            
            # Get performance metrics
            print("\n--- Performance Metrics ---")
            performance = await performance_tool.execute(
                account_id=account,
                period="month"
            )
            print(performance)
            
            # Get cash flows
            print("\n--- Cash Flows (Last Month) ---")
            cash_flows = await cash_flow_tool.execute(
                account_id=account,
                from_date=start_date
            )
            print(cash_flows)
            
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main()) 