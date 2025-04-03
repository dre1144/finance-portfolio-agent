import logging
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

from tinkoff.invest.grpc.marketdata_pb2 import CandleInterval

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
    
    # Check for token
    token = os.getenv('TINKOFF_TOKEN')
    if not token:
        logger.error("TINKOFF_TOKEN environment variable not set")
        return
    
    # Remove quotes if present
    token = token.strip('"')
    
    client = TinkoffClient(token)
    try:
        # Get accounts to find instruments
        accounts = client.get_accounts()
        logger.info(f"Found {len(accounts)} accounts")
        
        if not accounts:
            logger.error("No accounts found")
            return
            
        # Use first account to get portfolio
        account_id = accounts[0]['id']
        portfolio = client.get_portfolio(account_id)
        logger.info(f"Got portfolio with {len(portfolio['positions'])} positions")
        
        if not portfolio['positions']:
            logger.error("No positions found in portfolio")
            return
            
        # Get candles for first position
        position = portfolio['positions'][0]
        figi = position['figi']
        logger.info(f"Getting candles for {figi}")
        
        # Test different intervals
        intervals = [
            (CandleInterval.CANDLE_INTERVAL_1_MIN, "1 minute"),
            (CandleInterval.CANDLE_INTERVAL_HOUR, "1 hour"),
            (CandleInterval.CANDLE_INTERVAL_DAY, "1 day")
        ]
        
        end_date = datetime.now()
        for interval, name in intervals:
            # Get data for last 7 days
            start_date = end_date - timedelta(days=7)
            logger.info(f"Getting {name} candles from {start_date} to {end_date}")
            
            candles = client.get_candles(figi, start_date, end_date, interval)
            logger.info(f"Got {len(candles)} {name} candles")
            
            if candles:
                sample_candle = candles[0]
                logger.info(f"Sample candle: {sample_candle}")
        
        # Test get_all_candles with 30 days of daily data
        start_date = end_date - timedelta(days=30)
        logger.info(f"Getting all daily candles from {start_date} to {end_date}")
        
        all_candles = client.get_all_candles(
            figi, 
            start_date, 
            end_date,
            CandleInterval.CANDLE_INTERVAL_DAY
        )
        logger.info(f"Got {len(all_candles)} daily candles in total")
        
    finally:
        client.close()

if __name__ == '__main__':
    main() 