"""
Test script for Tinkoff Invest portfolio information.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

from src.services.tinkoff.client import TinkoffClient
from src.services.tinkoff.portfolio import PortfolioService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Run portfolio information test."""
    # Load environment variables
    load_dotenv()
    token = os.getenv("TINKOFF_TOKEN")
    if not token:
        raise ValueError("TINKOFF_TOKEN environment variable is not set")

    try:
        # Initialize client and service
        client = TinkoffClient(token=token)
        service = PortfolioService(client)

        # Get accounts
        logger.info("Getting accounts...")
        accounts = await service.get_accounts()
        logger.info("Found accounts: %s", accounts)

        if not accounts:
            logger.warning("No accounts found")
            return

        # Use first account for testing
        account_id = accounts[0]["id"]
        logger.info("Using account: %s", account_id)

        # Get portfolio
        logger.info("Getting portfolio...")
        portfolio = await service.get_portfolio(account_id)
        logger.info("Portfolio summary:")
        logger.info("- Total amount shares: %s", portfolio["total_amount_shares"])
        logger.info("- Total amount bonds: %s", portfolio["total_amount_bonds"])
        logger.info("- Total amount ETF: %s", portfolio["total_amount_etf"])
        logger.info("- Total amount currencies: %s", portfolio["total_amount_currencies"])
        logger.info("- Expected yield: %s", portfolio["expected_yield"])
        logger.info("- Number of positions: %d", len(portfolio["positions"]))

        # Get operations for last 7 days
        from_date = datetime.now() - timedelta(days=7)
        logger.info("Getting operations from %s...", from_date)
        operations = await service.get_operations(
            account_id=account_id,
            from_date=from_date
        )
        logger.info("Found %d operations", len(operations["operations"]))

    except Exception as e:
        logger.error("Error occurred: %s", str(e), exc_info=True)
    finally:
        # Close client
        await client.close()

if __name__ == "__main__":
    asyncio.run(main()) 