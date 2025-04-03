import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

from src.services.tinkoff.client import TinkoffClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    # Load environment variables
    load_dotenv()
    token = os.getenv('TINKOFF_TOKEN')
    
    if not token:
        logger.error("TINKOFF_TOKEN environment variable is not set")
        return
    
    # Initialize client
    client = TinkoffClient(token)
    logger.info("Initialized Tinkoff client")
    
    try:
        # Get all instruments
        instruments = client.get_all_instruments()
        
        # Print summary
        logger.info("=== Available Instruments Summary ===")
        logger.info(f"Total shares: {len(instruments['shares'])}")
        logger.info(f"Total bonds: {len(instruments['bonds'])}")
        logger.info(f"Total ETFs: {len(instruments['etfs'])}")
        
        # Print some examples of each type
        logger.info("\n=== Example Shares ===")
        for share in instruments['shares'][:3]:
            logger.info(f"Name: {share['name']}")
            logger.info(f"Ticker: {share['ticker']}")
            logger.info(f"FIGI: {share['figi']}")
            logger.info(f"Currency: {share['currency']}")
            logger.info(f"Sector: {share['sector']}")
            logger.info(f"Trading status: {share['trading_status']}")
            logger.info(f"Buy available: {share['buy_available']}")
            logger.info(f"Sell available: {share['sell_available']}")
            logger.info("---")
        
        logger.info("\n=== Example Bonds ===")
        for bond in instruments['bonds'][:3]:
            logger.info(f"Name: {bond['name']}")
            logger.info(f"Ticker: {bond['ticker']}")
            logger.info(f"FIGI: {bond['figi']}")
            logger.info(f"Currency: {bond['currency']}")
            logger.info(f"Nominal: {bond['nominal']}")
            logger.info(f"Maturity date: {bond['maturity_date']}")
            logger.info(f"Coupon quantity per year: {bond['coupon_quantity_per_year']}")
            logger.info(f"Current ACI: {bond['current_aci']}")
            logger.info("---")
        
        logger.info("\n=== Example ETFs ===")
        for etf in instruments['etfs'][:3]:
            logger.info(f"Name: {etf['name']}")
            logger.info(f"Ticker: {etf['ticker']}")
            logger.info(f"FIGI: {etf['figi']}")
            logger.info(f"Currency: {etf['currency']}")
            logger.info(f"Focus type: {etf['focus_type']}")
            logger.info(f"Fixed commission: {etf['fixed_commission']}")
            logger.info(f"Rebalancing frequency: {etf['rebalancing_freq']}")
            logger.info("---")
            
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    main() 