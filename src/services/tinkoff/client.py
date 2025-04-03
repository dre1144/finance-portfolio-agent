"""
Tinkoff Invest API client implementation with Supabase token management.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

import grpc
import pytz
from google.protobuf.timestamp_pb2 import Timestamp
from tinkoff.invest.grpc.users_pb2_grpc import UsersServiceStub
from tinkoff.invest.grpc.users_pb2 import GetAccountsRequest
from tinkoff.invest.grpc.operations_pb2_grpc import OperationsServiceStub
from tinkoff.invest.grpc.operations_pb2 import PortfolioRequest, OperationsRequest
from tinkoff.invest.grpc.marketdata_pb2_grpc import MarketDataServiceStub
from tinkoff.invest.grpc.marketdata_pb2 import (
    GetCandlesRequest,
    CandleInterval,
    GetOrderBookRequest,
    GetLastPricesRequest,
    GetTradingStatusRequest
)
from tinkoff.invest.grpc.instruments_pb2_grpc import InstrumentsServiceStub
from tinkoff.invest.grpc.instruments_pb2 import (
    InstrumentStatus,
    InstrumentIdType,
    SharesResponse,
    BondsResponse,
    EtfsResponse,
    InstrumentsRequest,
    GetDividendsRequest,
    GetBondCouponsRequest,
    GetAccruedInterestsRequest
)
from tinkoff.invest.constants import INVEST_GRPC_API
from tinkoff.invest.utils import quotation_to_decimal, now

from .exceptions import TinkoffAuthError, TinkoffNetworkError
from ..supabase.token_service import TokenService

logger = logging.getLogger(__name__)

def _datetime_to_timestamp(dt: datetime) -> Timestamp:
    """Convert datetime to Protobuf Timestamp."""
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    else:
        dt = dt.astimezone(pytz.UTC)
    ts = Timestamp()
    ts.FromDatetime(dt)
    return ts

class TinkoffClient:
    """
    Client for Tinkoff Invest API using gRPC with Supabase token management.
    """

    def __init__(self, token_service: TokenService, user_id: str):
        """Initialize client with token service and user ID."""
        self.token_service = token_service
        self.user_id = user_id
        self.channel = None
        self.users_stub = None
        self.operations_stub = None
        self.market_data_stub = None
        self.instruments_stub = None
        logger.info("Initialized TinkoffClient for user %s", user_id)

    async def _ensure_token(self) -> str:
        """Get and validate token from token service."""
        token = await self.token_service.get_token(self.user_id, 'tinkoff')
        if not token:
            raise TinkoffAuthError("No token found for user")
        return token

    async def _ensure_connection(self):
        """Ensure gRPC channel and stubs are initialized with valid token."""
        if not self.channel:
            token = await self._ensure_token()
            self.metadata = (('authorization', f'Bearer {token}'),)
            self.channel = self._get_channel()
            self.users_stub = UsersServiceStub(self.channel)
            self.operations_stub = OperationsServiceStub(self.channel)
            self.market_data_stub = MarketDataServiceStub(self.channel)
            self.instruments_stub = InstrumentsServiceStub(self.channel)

    def _get_channel(self) -> grpc.Channel:
        """Get or create gRPC channel."""
        return grpc.secure_channel(
            INVEST_GRPC_API,
            grpc.ssl_channel_credentials()
        )

    async def validate_token(self) -> bool:
        """Validate token by making a test API call."""
        try:
            await self._ensure_connection()
            await self.get_accounts()
            return True
        except TinkoffAuthError:
            return False
        except Exception as e:
            logger.error("Error validating token: %s", e)
            return False

    async def get_accounts(self) -> List[Dict[str, Any]]:
        """Get list of accounts."""
        await self._ensure_connection()
        logger.info("Getting accounts for user %s", self.user_id)
        try:
            response = self.users_stub.GetAccounts(GetAccountsRequest(), metadata=self.metadata)
            accounts = [
                {
                    "id": account.id,
                    "type": str(account.type),
                    "name": account.name,
                    "status": str(account.status),
                    "opened_date": account.opened_date.ToDatetime() if account.opened_date else None
                }
                for account in response.accounts
            ]
            logger.info("Found %d accounts", len(accounts))
            return accounts
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.UNAUTHENTICATED:
                # Инвалидируем токен в Supabase
                await self.token_service.invalidate_token(self.user_id, 'tinkoff')
                raise TinkoffAuthError("Invalid or expired token")
            raise TinkoffNetworkError(f"gRPC error: {e.details()}")

    async def get_portfolio(self, account_id: str) -> Dict[str, Any]:
        """Get portfolio for specified account."""
        await self._ensure_connection()
        logger.info("Getting portfolio for account %s", account_id)
        try:
            response = self.operations_stub.GetPortfolio(
                PortfolioRequest(account_id=account_id),
                metadata=self.metadata
            )
            
            result = {
                "total_amount_shares": quotation_to_decimal(response.total_amount_shares),
                "total_amount_bonds": quotation_to_decimal(response.total_amount_bonds),
                "total_amount_etf": quotation_to_decimal(response.total_amount_etf),
                "total_amount_currencies": quotation_to_decimal(response.total_amount_currencies),
                "total_amount_futures": quotation_to_decimal(response.total_amount_futures) if hasattr(response, 'total_amount_futures') else None,
                "total_amount_options": quotation_to_decimal(response.total_amount_options) if hasattr(response, 'total_amount_options') else None,
                "expected_yield": quotation_to_decimal(response.expected_yield),
                "positions": [
                    {
                        "figi": pos.figi,
                        "instrument_type": str(pos.instrument_type),
                        "quantity": quotation_to_decimal(pos.quantity),
                        "average_position_price": quotation_to_decimal(pos.average_position_price),
                        "expected_yield": quotation_to_decimal(pos.expected_yield),
                        "current_price": quotation_to_decimal(pos.current_price),
                        "current_nkd": quotation_to_decimal(pos.current_nkd) if pos.current_nkd else None,
                        "var_margin": quotation_to_decimal(pos.var_margin) if hasattr(pos, 'var_margin') else None,
                        "expected_yield_fifo": quotation_to_decimal(pos.expected_yield_fifo) if hasattr(pos, 'expected_yield_fifo') else None
                    }
                    for pos in response.positions
                ]
            }
            
            logger.info("Got portfolio with %d positions", len(result["positions"]))
            return result
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.UNAUTHENTICATED:
                await self.token_service.invalidate_token(self.user_id, 'tinkoff')
                raise TinkoffAuthError("Invalid or expired token")
            raise TinkoffNetworkError(f"gRPC error: {e.details()}")

    def close(self):
        """Close gRPC channel."""
        if self.channel:
            self.channel.close()
            self.channel = None
            self.users_stub = None
            self.operations_stub = None
            self.market_data_stub = None
            self.instruments_stub = None

    async def get_operations(
        self,
        account_id: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get operations for specified account."""
        logger.info("Getting operations for account %s", account_id)
        
        request = OperationsRequest(
            account_id=account_id,
            **{'from': _datetime_to_timestamp(from_date) if from_date else None},
            to=_datetime_to_timestamp(to_date) if to_date else None,
        )
        
        response = self.operations_stub.GetOperations(request, metadata=self.metadata)
        
        # Debug: print all available fields
        if response.operations:
            op = response.operations[0]
            if op.trades:
                trade = op.trades[0]
                logger.info("OperationTrade fields: %s", dir(trade))
        
        return [
            {
                "id": op.id,
                "type": str(op.type),
                "date": op.date.ToDatetime() if op.date else None,
                "figi": op.figi,
                "instrument_type": str(op.instrument_type),
                "payment": quotation_to_decimal(op.payment) if op.payment else None,
                "currency": op.currency,
                "commission": None,  # Commission is not available in the API response
                "tax": None,  # Tax is not available in the API response
            }
            for op in response.operations
        ] 