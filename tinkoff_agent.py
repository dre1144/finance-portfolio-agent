from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from tinkoff.invest import Client, OperationState, OperationType, InstrumentIdType, InstrumentStatus, SharesResponse, BondsResponse, EtfsResponse, CandleInterval, HistoricCandle, GetOrderBookResponse, Quotation, OrderBookInstrument
from datetime import datetime, time, timedelta, date
from typing import List, Optional, Dict, Tuple, Any
import pytz
import logging
import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum
import time as time_lib
from functools import wraps

class RecommendationType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

@dataclass
class InstrumentInfo:
    figi: str
    ticker: str
    name: str
    lot: int
    currency: str
    country: str
    sector: str
    exchange: str
    isin: str
    instrument_type: str
    min_price_increment: float
    scale: int
    trading_status: str

@dataclass
class PortfolioRecommendation:
    instrument_info: InstrumentInfo
    action: RecommendationType
    target_weight: float
    current_weight: float
    quantity: int
    expected_price: float
    reasoning: List[str]
    risk_metrics: Dict[str, float]
    historical_performance: Dict[str, float]

def retry_on_connection_error(max_retries=3, delay=1):
    """Декоратор для повторных попыток при ошибках подключения"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        raise
                    logging.warning(f"Connection error in {func.__name__}, retrying... ({retries}/{max_retries})")
                    time_lib.sleep(delay)
            return None
        return wrapper
    return decorator

class MarketDataAnalyzer:
    def __init__(self, client: Client):
        self.client = client
        self.logger = logging.getLogger('market_data_analyzer')

    @retry_on_connection_error()
    def get_orderbook(self, figi: str, depth: int = 20) -> Optional[GetOrderBookResponse]:
        """Получение стакана для оценки ликвидности"""
        try:
            return self.client.market_data.get_order_book(
                figi=figi,
                depth=depth
            )
        except Exception as e:
            self.logger.error(f"Error getting orderbook for {figi}: {e}")
            return None

    @retry_on_connection_error()
    def get_historical_data(self, figi: str, from_date: datetime, to_date: datetime, 
                          interval: CandleInterval = CandleInterval.CANDLE_INTERVAL_DAY) -> List[HistoricCandle]:
        """Получение исторических данных с повторными попытками"""
        try:
            candles = self.client.market_data.get_candles(
                figi=figi,
                from_=from_date,
                to=to_date,
                interval=interval
            )
            return candles.candles
        except Exception as e:
            self.logger.error(f"Error getting historical data for {figi}: {e}")
            return []

    def calculate_liquidity_metrics(self, orderbook: GetOrderBookResponse) -> Dict[str, float]:
        """Расчет метрик ликвидности на основе стакана"""
        if not orderbook:
            return {
                "spread_percentage": 0,
                "depth_volume": 0,
                "weighted_average_spread": 0
            }

        try:
            # Спред
            best_bid = orderbook.bids[0].price if orderbook.bids else None
            best_ask = orderbook.asks[0].price if orderbook.asks else None
            
            if best_bid and best_ask:
                bid_price = best_bid.units + best_bid.nano / 1e9
                ask_price = best_ask.units + best_ask.nano / 1e9
                mid_price = (bid_price + ask_price) / 2
                spread_percentage = (ask_price - bid_price) / mid_price * 100
            else:
                spread_percentage = 0

            # Объем в стакане
            total_volume = sum(bid.quantity for bid in orderbook.bids) + \
                         sum(ask.quantity for ask in orderbook.asks)

            # Взвешенный спред
            weighted_spread = 0
            total_weight = 0
            
            for i in range(min(len(orderbook.bids), len(orderbook.asks))):
                bid = orderbook.bids[i].price
                ask = orderbook.asks[i].price
                volume = (orderbook.bids[i].quantity + orderbook.asks[i].quantity) / 2
                
                bid_price = bid.units + bid.nano / 1e9
                ask_price = ask.units + ask.nano / 1e9
                spread = ask_price - bid_price
                
                weighted_spread += spread * volume
                total_weight += volume

            weighted_average_spread = weighted_spread / total_weight if total_weight > 0 else 0

            return {
                "spread_percentage": round(spread_percentage, 4),
                "depth_volume": round(total_volume, 2),
                "weighted_average_spread": round(weighted_average_spread, 4)
            }

        except Exception as e:
            self.logger.error(f"Error calculating liquidity metrics: {e}")
            return {
                "spread_percentage": 0,
                "depth_volume": 0,
                "weighted_average_spread": 0
            }

    def calculate_correlation_matrix(self, figis: List[str], 
                                   from_date: datetime, 
                                   to_date: datetime) -> pd.DataFrame:
        """Расчет матрицы корреляций между инструментами"""
        price_data = {}
        
        for figi in figis:
            candles = self.get_historical_data(figi, from_date, to_date)
            if candles:
                prices = [candle.close.units + candle.close.nano / 1e9 for candle in candles]
                price_data[figi] = pd.Series(prices)

        if not price_data:
            return pd.DataFrame()

        # Создаем DataFrame и считаем корреляции
        df = pd.DataFrame(price_data)
        return df.pct_change().corr()

    def calculate_advanced_risk_metrics(self, prices: List[float], risk_free_rate: float = 0.045) -> Dict[str, float]:
        """Расчет расширенных метрик риска"""
        if not prices or len(prices) < 2:
            return {
                "volatility": 0,
                "sharpe_ratio": 0,
                "sortino_ratio": 0,
                "max_drawdown": 0,
                "var_95": 0,
                "var_99": 0,
                "skewness": 0,
                "kurtosis": 0
            }

        returns = pd.Series(prices).pct_change().dropna()
        
        # Волатильность
        volatility = returns.std() * np.sqrt(252)
        
        # Доходность
        annual_return = returns.mean() * 252
        excess_return = annual_return - risk_free_rate
        
        # Коэффициент Шарпа
        sharpe_ratio = excess_return / volatility if volatility != 0 else 0
        
        # Коэффициент Сортино
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() * np.sqrt(252)
        sortino_ratio = excess_return / downside_std if downside_std != 0 else 0
        
        # Максимальная просадка
        cum_returns = (1 + returns).cumprod()
        running_max = cum_returns.cummax()
        drawdowns = (cum_returns - running_max) / running_max
        max_drawdown = abs(drawdowns.min())
        
        # Value at Risk
        var_95 = abs(np.percentile(returns, 5))
        var_99 = abs(np.percentile(returns, 1))
        
        # Асимметрия и эксцесс
        skewness = returns.skew()
        kurtosis = returns.kurtosis()

        return {
            "volatility": round(volatility * 100, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "sortino_ratio": round(sortino_ratio, 2),
            "max_drawdown": round(max_drawdown * 100, 2),
            "var_95": round(var_95 * 100, 2),
            "var_99": round(var_99 * 100, 2),
            "skewness": round(skewness, 2),
            "kurtosis": round(kurtosis, 2)
        }

class TinkoffAgent:
    def __init__(self, client: Client, config: dict):
        self.client = client
        self.config = config
        self.logger = logging.getLogger('tinkoff_agent')
        self.market_analyzer = MarketDataAnalyzer(client)
        self.app = FastAPI(title="Tinkoff Trading Agent")
        self.setup_routes()

    def get_all_accounts(self) -> List[dict]:
        """Получение списка всех счетов"""
        try:
            accounts = self.client.users.get_accounts()
            return [
                {
                    "id": acc.id,
                    "name": acc.name,
                    "type": str(acc.type),
                    "status": str(acc.status),
                    "opened_date": acc.opened_date.isoformat() if acc.opened_date else None,
                    "closed_date": acc.closed_date.isoformat() if acc.closed_date else None,
                    "access_level": str(acc.access_level)
                }
                for acc in accounts.accounts
            ]
        except Exception as e:
            self.logger.error(f"Error getting accounts: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def get_historical_operations_all_accounts(self, from_date: datetime, to_date: datetime) -> Dict[str, List[dict]]:
        """Получение исторических операций за период по всем счетам"""
        accounts = self.get_all_accounts()
        operations_by_account = {}

        for account in accounts:
            try:
                # Convert to UTC timezone for Tinkoff API
                from_date_utc = from_date.astimezone(pytz.UTC)
                to_date_utc = to_date.astimezone(pytz.UTC)
                
                operations = self.client.operations.get_operations(
                    account_id=account['id'],
                    from_=from_date_utc,
                    to=to_date_utc,
                    state=OperationState.OPERATION_STATE_EXECUTED
                )
                
                operations_by_account[account['id']] = [
                    {
                        "id": op.id,
                        "type": str(op.type),
                        "date": op.date.strftime("%Y-%m-%d %H:%M:%S"),
                        "instrument_type": str(op.instrument_type),
                        "figi": op.figi,
                        "quantity": op.quantity,
                        "payment": op.payment.units + op.payment.nano / 1e9 if op.payment else 0,
                        "currency": op.currency,
                        "price": op.price.units + op.price.nano / 1e9 if op.price else 0,
                        "account_id": account['id'],
                        "account_name": account['name']
                    }
                    for op in operations.operations
                ]
            except Exception as e:
                self.logger.error(f"Error getting operations for account {account['id']}: {e}")
                operations_by_account[account['id']] = []

        return operations_by_account

    def get_portfolio_all_accounts(self) -> Dict[str, dict]:
        """Получение портфеля по всем счетам"""
        accounts = self.get_all_accounts()
        portfolios = {}

        for account in accounts:
            try:
                portfolio = self.client.operations.get_portfolio(account_id=account['id'])
                portfolios[account['id']] = {
                    "account_name": account['name'],
                    "total_amount": {
                        "currency": portfolio.total_amount_portfolio.currency,
                        "value": portfolio.total_amount_portfolio.units + portfolio.total_amount_portfolio.nano / 1e9
                    },
                    "positions": [
                        {
                            "figi": pos.figi,
                            "quantity": pos.quantity.units,
                            "average_price": pos.average_position_price.units + pos.average_position_price.nano / 1e9
                        }
                        for pos in portfolio.positions
                    ]
                }
            except Exception as e:
                self.logger.error(f"Error getting portfolio for account {account['id']}: {e}")
                portfolios[account['id']] = {
                    "account_name": account['name'],
                    "total_amount": {"currency": "rub", "value": 0},
                    "positions": []
                }

        return portfolios

    def calculate_pnl_all_accounts(self, operations_by_account: Dict[str, List[dict]]) -> dict:
        """Расчет P&L на основе операций по всем счетам"""
        total_pnl = 0
        pnl_by_account = {}
        all_instruments = {}
        all_types = {}

        for account_id, operations in operations_by_account.items():
            df = pd.DataFrame(operations)
            if df.empty:
                pnl_by_account[account_id] = {
                    "account_name": operations[0]['account_name'] if operations else "Unknown",
                    "total_pnl": 0,
                    "by_instrument": {},
                    "by_type": {}
                }
                continue

            # Конвертируем даты
            df['date'] = pd.to_datetime(df['date'])
            
            # Расчет P&L по инструментам для текущего счета
            pnl_by_instrument = df.groupby('figi')['payment'].sum().to_dict()
            
            # Расчет P&L по типам операций для текущего счета
            pnl_by_type = df.groupby('type')['payment'].sum().to_dict()
            
            account_total_pnl = float(df['payment'].sum())
            total_pnl += account_total_pnl

            # Обновляем общую статистику по инструментам и типам
            for figi, amount in pnl_by_instrument.items():
                all_instruments[figi] = all_instruments.get(figi, 0) + amount
            for op_type, amount in pnl_by_type.items():
                all_types[op_type] = all_types.get(op_type, 0) + amount

            pnl_by_account[account_id] = {
                "account_name": operations[0]['account_name'] if operations else "Unknown",
                "total_pnl": account_total_pnl,
                "by_instrument": {k: float(v) for k, v in pnl_by_instrument.items()},
                "by_type": {k: float(v) for k, v in pnl_by_type.items()}
            }

        return {
            "total_pnl": float(total_pnl),
            "by_account": pnl_by_account,
            "total_by_instrument": {k: float(v) for k, v in all_instruments.items()},
            "total_by_type": {k: float(v) for k, v in all_types.items()}
        }

    def calculate_expenses_by_category(self, operations: List[dict]) -> dict:
        """Расчет расходов по категориям"""
        df = pd.DataFrame(operations)
        if df.empty:
            return {
                "total_expenses": 0,
                "categories": {
                    "commissions": {"sum": 0, "count": 0, "percentage": 0},
                    "taxes": {"sum": 0, "count": 0, "percentage": 0},
                    "investments": {"sum": 0, "count": 0, "percentage": 0},
                    "withdrawals": {"sum": 0, "count": 0, "percentage": 0}
                }
            }

        # Комиссии
        commissions = df[df['type'].str.contains('комисси', case=False, na=False)]
        commission_sum = abs(float(commissions['payment'].sum()))
        commission_count = len(commissions)

        # Налоги (включая удержания и корректировки)
        taxes = df[df['type'].str.contains('налог', case=False, na=False)]
        tax_sum = abs(float(taxes[taxes['payment'] < 0]['payment'].sum()))
        tax_count = len(taxes[taxes['payment'] < 0])

        # Инвестиции (покупка ценных бумаг)
        investments = df[df['type'].str.contains('покупка', case=False, na=False)]
        investment_sum = abs(float(investments['payment'].sum()))
        investment_count = len(investments)

        # Выводы средств
        withdrawals = df[df['type'].str.contains('вывод', case=False, na=False)]
        withdrawal_sum = abs(float(withdrawals['payment'].sum()))
        withdrawal_count = len(withdrawals)

        total_expenses = commission_sum + tax_sum + investment_sum + withdrawal_sum

        # Расчет процентов
        def safe_percentage(value: float, total: float) -> float:
            return round((value / total * 100) if total > 0 else 0, 2)

        return {
            "total_expenses": float(total_expenses),
            "categories": {
                "commissions": {
                    "sum": float(commission_sum),
                    "count": int(commission_count),
                    "percentage": safe_percentage(commission_sum, total_expenses)
                },
                "taxes": {
                    "sum": float(tax_sum),
                    "count": int(tax_count),
                    "percentage": safe_percentage(tax_sum, total_expenses)
                },
                "investments": {
                    "sum": float(investment_sum),
                    "count": int(investment_count),
                    "percentage": safe_percentage(investment_sum, total_expenses)
                },
                "withdrawals": {
                    "sum": float(withdrawal_sum),
                    "count": int(withdrawal_count),
                    "percentage": safe_percentage(withdrawal_sum, total_expenses)
                }
            }
        }

    def calculate_cash_flow_all_accounts(self, operations_by_account: Dict[str, List[dict]]) -> dict:
        """Расчет Cash Flow на основе операций по всем счетам"""
        total_inflow = 0
        total_outflow = 0
        cash_flow_by_account = {}
        all_types = {}
        all_expenses = {
            "total_expenses": 0,
            "categories": {
                "commissions": {"sum": 0, "count": 0, "percentage": 0},
                "taxes": {"sum": 0, "count": 0, "percentage": 0},
                "investments": {"sum": 0, "count": 0, "percentage": 0},
                "withdrawals": {"sum": 0, "count": 0, "percentage": 0}
            }
        }

        # Временный словарь для сбора всех расходов по счетам
        accounts_expenses = []

        for account_id, operations in operations_by_account.items():
            df = pd.DataFrame(operations)
            if df.empty:
                account_expenses = self.calculate_expenses_by_category(operations)
                cash_flow_by_account[account_id] = {
                    "account_name": operations[0]['account_name'] if operations else "Unknown",
                    "inflow": 0,
                    "outflow": 0,
                    "net_flow": 0,
                    "by_type": {},
                    "expenses": account_expenses
                }
                continue

            df['date'] = pd.to_datetime(df['date'])
            
            # Расчет потоков для текущего счета
            inflow = float(df[df['payment'] > 0]['payment'].sum())
            outflow = float(abs(df[df['payment'] < 0]['payment'].sum()))
            
            total_inflow += inflow
            total_outflow += outflow

            # Расчет потоков по типам операций
            flow_by_type = df.groupby('type').agg({
                'payment': ['sum', 'count']
            }).round(2)
            
            flow_by_type_dict = {
                type_: {
                    "sum": float(data['sum']),
                    "count": int(data['count'])
                }
                for type_, data in flow_by_type.payment.to_dict('index').items()
            }

            # Обновляем общую статистику по типам
            for op_type, data in flow_by_type_dict.items():
                if op_type not in all_types:
                    all_types[op_type] = {"sum": 0, "count": 0}
                all_types[op_type]["sum"] += data["sum"]
                all_types[op_type]["count"] += data["count"]

            # Расчет расходов по категориям
            account_expenses = self.calculate_expenses_by_category(operations)
            
            # Сохраняем информацию о расходах счета для последующего анализа
            if account_expenses["total_expenses"] > 0:
                accounts_expenses.append({
                    "account_id": account_id,
                    "account_name": operations[0]['account_name'] if operations else "Unknown",
                    "expenses": account_expenses
                })
            
            # Обновляем общие расходы
            all_expenses["total_expenses"] += account_expenses["total_expenses"]
            for category in ["commissions", "taxes", "investments", "withdrawals"]:
                all_expenses["categories"][category]["sum"] += account_expenses["categories"][category]["sum"]
                all_expenses["categories"][category]["count"] += account_expenses["categories"][category]["count"]

            cash_flow_by_account[account_id] = {
                "account_name": operations[0]['account_name'] if operations else "Unknown",
                "inflow": inflow,
                "outflow": outflow,
                "net_flow": inflow - outflow,
                "by_type": flow_by_type_dict,
                "expenses": account_expenses
            }

        # Расчет процентов для общих расходов
        if all_expenses["total_expenses"] > 0:
            for category in all_expenses["categories"]:
                all_expenses["categories"][category]["percentage"] = round(
                    all_expenses["categories"][category]["sum"] / all_expenses["total_expenses"] * 100,
                    2
                )

        # Сортируем счета по общей сумме расходов
        accounts_expenses.sort(key=lambda x: x["expenses"]["total_expenses"], reverse=True)
        
        # Добавляем сравнение расходов между счетами
        accounts_comparison = []
        if accounts_expenses:
            total_all_accounts = sum(acc["expenses"]["total_expenses"] for acc in accounts_expenses)
            for acc in accounts_expenses:
                percentage_of_total = round(acc["expenses"]["total_expenses"] / total_all_accounts * 100, 2)
                accounts_comparison.append({
                    "account_name": acc["account_name"],
                    "total_expenses": acc["expenses"]["total_expenses"],
                    "percentage_of_total": percentage_of_total,
                    "categories": acc["expenses"]["categories"]
                })

        return {
            "total_inflow": float(total_inflow),
            "total_outflow": float(total_outflow),
            "total_net_flow": float(total_inflow - total_outflow),
            "by_account": cash_flow_by_account,
            "total_by_type": all_types,
            "total_expenses": all_expenses,
            "accounts_comparison": accounts_comparison
        }

    def calculate_portfolio_performance_all_accounts(self, operations_by_account: Dict[str, List[dict]], portfolios: Dict[str, dict]) -> dict:
        """Расчет показателей эффективности по всем счетам"""
        total_invested = 0
        total_current_value = 0
        performance_by_account = {}

        for account_id, operations in operations_by_account.items():
            df = pd.DataFrame(operations)
            current_portfolio = portfolios.get(account_id, {
                "total_amount": {"value": 0},
                "positions": []
            })

            if df.empty:
                performance_by_account[account_id] = {
                    "account_name": operations[0]['account_name'] if operations else "Unknown",
                    "total_invested": 0,
                    "current_value": current_portfolio['total_amount']['value'],
                    "total_return": 0,
                    "return_percentage": 0
                }
                continue

            df['date'] = pd.to_datetime(df['date'])
            
            # Расчет общей суммы инвестиций для текущего счета
            account_invested = float(abs(df[df['payment'] < 0]['payment'].sum()))
            total_invested += account_invested
            
            # Текущая стоимость портфеля
            current_value = float(current_portfolio['total_amount']['value'])
            total_current_value += current_value
            
            # Расчет доходности
            total_return = current_value - account_invested
            return_percentage = (total_return / account_invested * 100) if account_invested != 0 else 0

            performance_by_account[account_id] = {
                "account_name": operations[0]['account_name'] if operations else "Unknown",
                "total_invested": account_invested,
                "current_value": current_value,
                "total_return": total_return,
                "return_percentage": float(return_percentage)
            }

        # Расчет общей доходности
        total_return = total_current_value - total_invested
        total_return_percentage = (total_return / total_invested * 100) if total_invested != 0 else 0

        return {
            "total_invested": float(total_invested),
            "total_current_value": float(total_current_value),
            "total_return": float(total_return),
            "total_return_percentage": float(total_return_percentage),
            "by_account": performance_by_account
        }

    @retry_on_connection_error()
    def get_instrument_info(self, figi: str) -> InstrumentInfo:
        """Получение детальной информации об инструменте с повторными попытками"""
        try:
            instrument = self.client.instruments.get_instrument_by(
                id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI,
                id=figi
            )
            if hasattr(instrument, 'instrument'):
                i = instrument.instrument
                return InstrumentInfo(
                    figi=i.figi,
                    ticker=i.ticker,
                    name=i.name,
                    lot=i.lot,
                    currency=i.currency,
                    country=i.country_of_risk,
                    sector=i.sector,
                    exchange=i.exchange,
                    isin=i.isin,
                    instrument_type=i.instrument_type,
                    min_price_increment=i.min_price_increment.units + i.min_price_increment.nano / 1e9,
                    scale=i.scale,
                    trading_status=str(i.trading_status)
                )
        except Exception as e:
            self.logger.error(f"Error getting instrument info for {figi}: {e}")
            return None

    def analyze_portfolio_risk(self, portfolio: dict, from_date: datetime, to_date: datetime) -> Dict[str, Any]:
        """Комплексный анализ риска портфеля"""
        # Получаем все FIGI из портфеля
        figis = [pos['figi'] for pos in portfolio['positions'] if pos['figi']]
        
        # Рассчитываем корреляции
        correlation_matrix = self.market_analyzer.calculate_correlation_matrix(figis, from_date, to_date)
        
        # Анализируем каждую позицию
        position_analysis = {}
        for position in portfolio['positions']:
            figi = position['figi']
            if not figi:
                continue
                
            # Получаем исторические данные
            candles = self.market_analyzer.get_historical_data(figi, from_date, to_date)
            prices = [candle.close.units + candle.close.nano / 1e9 for candle in candles]
            
            # Рассчитываем метрики риска
            risk_metrics = self.market_analyzer.calculate_advanced_risk_metrics(prices)
            
            # Получаем метрики ликвидности
            orderbook = self.market_analyzer.get_orderbook(figi)
            liquidity_metrics = self.market_analyzer.calculate_liquidity_metrics(orderbook)
            
            position_analysis[figi] = {
                "risk_metrics": risk_metrics,
                "liquidity_metrics": liquidity_metrics
            }
        
        return {
            "position_analysis": position_analysis,
            "correlation_matrix": correlation_matrix.to_dict() if not correlation_matrix.empty else {}
        }

    def generate_portfolio_recommendations(
        self,
        current_portfolio: dict,
        risk_profile: str = "moderate"
    ) -> List[PortfolioRecommendation]:
        """Генерация рекомендаций по оптимизации портфеля"""
        recommendations = []
        
        # Получаем данные за последний год
        from_date = datetime.now() - timedelta(days=365)
        to_date = datetime.now()
        
        # Анализируем текущий портфель
        portfolio_analysis = self.analyze_portfolio_composition(current_portfolio)
        risk_analysis = self.analyze_portfolio_risk(current_portfolio, from_date, to_date)
        
        # Получаем доступные инструменты
        available_instruments = self.get_available_instruments()
        
        # Для каждой позиции в портфеле
        for position in current_portfolio['positions']:
            figi = position['figi']
            if not figi:
                continue
                
            instrument = self.get_instrument_info(figi)
            if not instrument:
                continue
            
            # Получаем анализ риска для позиции
            position_risk = risk_analysis['position_analysis'].get(figi, {})
            risk_metrics = position_risk.get('risk_metrics', {})
            liquidity_metrics = position_risk.get('liquidity_metrics', {})
            
            # Рассчитываем текущий вес в портфеле
            position_value = position['quantity'] * position['average_price']
            current_weight = position_value / current_portfolio['total_amount']['value']
            
            # Анализируем необходимость ребалансировки
            reasoning = []
            action = RecommendationType.HOLD
            target_weight = current_weight
            
            # Проверяем метрики риска
            if risk_metrics.get('volatility', 0) > 30:
                reasoning.append(f"Высокая волатильность ({risk_metrics['volatility']}%)")
                action = RecommendationType.SELL
                target_weight = max(0, current_weight - 0.05)
            
            if risk_metrics.get('sharpe_ratio', 0) < 0.5:
                reasoning.append(f"Низкий коэффициент Шарпа ({risk_metrics['sharpe_ratio']})")
                action = RecommendationType.SELL
                target_weight = max(0, current_weight - 0.03)
            
            if risk_metrics.get('max_drawdown', 0) > 20:
                reasoning.append(f"Большая максимальная просадка ({risk_metrics['max_drawdown']}%)")
                action = RecommendationType.SELL
                target_weight = max(0, current_weight - 0.04)
            
            # Проверяем ликвидность
            if liquidity_metrics.get('spread_percentage', 0) > 1:
                reasoning.append(f"Высокий спред ({liquidity_metrics['spread_percentage']}%)")
                action = RecommendationType.SELL
                target_weight = max(0, current_weight - 0.02)
            
            # Проверяем концентрацию
            sector = portfolio_analysis['sector_exposure'].get(instrument.sector, 0)
            if sector > 0.25:
                reasoning.append(f"Высокая концентрация в секторе {instrument.sector} ({sector*100}%)")
                action = RecommendationType.SELL
                target_weight = max(0, current_weight - 0.05)
            
            # Если нужно продавать, ищем альтернативы для покупки
            if action == RecommendationType.SELL:
                alternatives = []
                for inst_type in ['shares', 'etfs']:
                    for alt_instrument in available_instruments[inst_type]:
                        if alt_instrument.sector != instrument.sector:
                            # Анализируем альтернативный инструмент
                            alt_candles = self.market_analyzer.get_historical_data(
                                alt_instrument.figi,
                                from_date,
                                to_date
                            )
                            alt_prices = [candle.close.units + candle.close.nano / 1e9 
                                        for candle in alt_candles]
                            alt_metrics = self.market_analyzer.calculate_advanced_risk_metrics(alt_prices)
                            
                            # Проверяем ликвидность
                            alt_orderbook = self.market_analyzer.get_orderbook(alt_instrument.figi)
                            alt_liquidity = self.market_analyzer.calculate_liquidity_metrics(alt_orderbook)
                            
                            if (alt_metrics['sharpe_ratio'] > risk_metrics.get('sharpe_ratio', 0) and
                                alt_metrics['volatility'] < risk_metrics.get('volatility', 100) and
                                alt_liquidity['spread_percentage'] < liquidity_metrics.get('spread_percentage', 100)):
                                alternatives.append((alt_instrument, alt_metrics, alt_liquidity))
                
                if alternatives:
                    # Выбираем лучшую альтернативу по соотношению риск/доходность и ликвидности
                    best_alternative = max(alternatives, 
                                        key=lambda x: (x[1]['sharpe_ratio'] / x[1]['volatility']) * 
                                                    (1 / (1 + x[2]['spread_percentage'])))
                    
                    alt_instrument, alt_metrics, alt_liquidity = best_alternative
                    
                    recommendations.append(PortfolioRecommendation(
                        instrument_info=alt_instrument,
                        action=RecommendationType.BUY,
                        target_weight=target_weight,
                        current_weight=0,
                        quantity=int(target_weight * current_portfolio['total_amount']['value'] / 
                                   (alt_prices[-1] if alt_prices else 0)),
                        expected_price=alt_prices[-1] if alt_prices else 0,
                        reasoning=[
                            f"Лучшие метрики риска (Sharpe: {alt_metrics['sharpe_ratio']}, "
                            f"Vol: {alt_metrics['volatility']}%)",
                            f"Лучшая ликвидность (Спред: {alt_liquidity['spread_percentage']}%)",
                            f"Диверсификация из сектора {instrument.sector} в {alt_instrument.sector}"
                        ],
                        risk_metrics=alt_metrics,
                        historical_performance={
                            "return_1y": (alt_prices[-1] / alt_prices[0] - 1) * 100 if len(alt_prices) > 1 else 0,
                            "avg_daily_volume": sum(1 for candle in alt_candles if candle.volume > 0) / len(alt_candles) if alt_candles else 0
                        }
                    ))
            
            # Добавляем рекомендацию по текущей позиции
            recommendations.append(PortfolioRecommendation(
                instrument_info=instrument,
                action=action,
                target_weight=target_weight,
                current_weight=current_weight,
                quantity=position['quantity'],
                expected_price=position['average_price'],
                reasoning=reasoning,
                risk_metrics=risk_metrics,
                historical_performance={
                    "return_1y": (prices[-1] / prices[0] - 1) * 100 if len(prices) > 1 else 0,
                    "avg_daily_volume": liquidity_metrics.get('depth_volume', 0)
                }
            ))
        
        return recommendations

    def setup_routes(self):
        @self.app.get("/health")
        def health_check():
            return {"status": "ok", "timestamp": datetime.now().isoformat()}

        @self.app.get("/accounts")
        def get_accounts():
            try:
                return {"accounts": self.get_all_accounts()}
            except Exception as e:
                self.logger.error(f"Error getting accounts: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/portfolio")
        def get_portfolio():
            try:
                return self.get_portfolio_all_accounts()
            except Exception as e:
                self.logger.error(f"Error getting portfolio: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/reports/pnl")
        def get_pnl_report(
            from_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
            to_date: date = Query(..., description="End date (YYYY-MM-DD)")
        ):
            try:
                self.logger.info(f"Received dates: from_date={from_date}, to_date={to_date}")
                from_dt = datetime.combine(from_date, time.min)
                to_dt = datetime.combine(to_date, time.max)
                self.logger.info(f"Parsed dates: from_dt={from_dt}, to_dt={to_dt}")
                operations = self.get_historical_operations_all_accounts(from_dt, to_dt)
                return self.calculate_pnl_all_accounts(operations)
            except Exception as e:
                self.logger.error(f"Error generating P&L report: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/reports/cash-flow")
        def get_cash_flow_report(
            from_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
            to_date: date = Query(..., description="End date (YYYY-MM-DD)")
        ):
            try:
                self.logger.info(f"Received dates: from_date={from_date}, to_date={to_date}")
                from_dt = datetime.combine(from_date, time.min)
                to_dt = datetime.combine(to_date, time.max)
                self.logger.info(f"Parsed dates: from_dt={from_dt}, to_dt={to_dt}")
                operations = self.get_historical_operations_all_accounts(from_dt, to_dt)
                return self.calculate_cash_flow_all_accounts(operations)
            except Exception as e:
                self.logger.error(f"Error generating Cash Flow report: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/reports/portfolio-performance")
        def get_portfolio_performance_report(
            from_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
            to_date: date = Query(..., description="End date (YYYY-MM-DD)")
        ):
            try:
                self.logger.info(f"Received dates: from_date={from_date}, to_date={to_date}")
                from_dt = datetime.combine(from_date, time.min)
                to_dt = datetime.combine(to_date, time.max)
                self.logger.info(f"Parsed dates: from_dt={from_dt}, to_dt={to_dt}")
                operations = self.get_historical_operations_all_accounts(from_dt, to_dt)
                portfolios = self.get_portfolio_all_accounts()
                return self.calculate_portfolio_performance_all_accounts(operations, portfolios)
            except Exception as e:
                self.logger.error(f"Error generating Portfolio Performance report: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/portfolio/recommendations")
        def get_portfolio_recommendations(
            risk_profile: str = Query("moderate", description="Risk profile (conservative/moderate/aggressive)")
        ):
            """Получение рекомендаций по оптимизации портфеля"""
            try:
                # Получаем текущий портфель по всем счетам
                portfolios = self.get_portfolio_all_accounts()
                
                all_recommendations = []
                for account_id, portfolio in portfolios.items():
                    recommendations = self.generate_portfolio_recommendations(
                        portfolio,
                        risk_profile
                    )
                    
                    # Форматируем рекомендации для ответа
                    formatted_recommendations = []
                    for rec in recommendations:
                        formatted_rec = {
                            "instrument": {
                                "figi": rec.instrument_info.figi,
                                "ticker": rec.instrument_info.ticker,
                                "name": rec.instrument_info.name,
                                "type": rec.instrument_info.instrument_type,
                                "sector": rec.instrument_info.sector,
                                "currency": rec.instrument_info.currency
                            },
                            "action": rec.action.value,
                            "current_weight": round(rec.current_weight * 100, 2),
                            "target_weight": round(rec.target_weight * 100, 2),
                            "quantity": rec.quantity,
                            "expected_price": round(rec.expected_price, 2),
                            "reasoning": rec.reasoning,
                            "risk_metrics": rec.risk_metrics,
                            "historical_performance": rec.historical_performance
                        }
                        formatted_recommendations.append(formatted_rec)
                    
                    all_recommendations.append({
                        "account_id": account_id,
                        "account_name": portfolio.get("account_name", "Unknown"),
                        "recommendations": formatted_recommendations
                    })
                
                return all_recommendations
                
            except Exception as e:
                self.logger.error(f"Error generating portfolio recommendations: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    def is_trading_time(self) -> bool:
        moscow_tz = pytz.timezone('Europe/Moscow')
        current_time = datetime.now(moscow_tz).time()
        start_time = time.fromisoformat(self.config['strategy']['trading_schedule']['start_time'])
        end_time = time.fromisoformat(self.config['strategy']['trading_schedule']['end_time'])
        return start_time <= current_time <= end_time

    def run(self, host: str = "0.0.0.0", port: int = 8000):
        import uvicorn
        self.logger.info(f"Starting agent on {host}:{port}")
        uvicorn.run(self.app, host=host, port=port) 