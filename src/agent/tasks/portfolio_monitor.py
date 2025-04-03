"""
Background task for monitoring portfolio changes.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from ...services.supabase.token_service import TokenService
from ...services.supabase.notification_service import NotificationService, NotificationType, NotificationPriority
from ...services.tinkoff.client import TinkoffClient

logger = logging.getLogger(__name__)

class PortfolioMonitor:
    """Portfolio monitoring task."""

    def __init__(
        self,
        token_service: TokenService,
        notification_service: NotificationService,
        config: Dict
    ):
        """Initialize monitor with services and config."""
        self.token_service = token_service
        self.notification_service = notification_service
        self.config = config
        self.change_threshold = config.get('change_threshold', 5.0)
        self.snapshot_table = 'portfolio_snapshots'
        logger.info("Initialized PortfolioMonitor with threshold %f%%", self.change_threshold)

    async def _get_portfolio_snapshot(self, client: TinkoffClient, account_id: str) -> Dict:
        """Get current portfolio snapshot."""
        portfolio = await client.get_portfolio(account_id)
        
        # Рассчитываем общую стоимость портфеля
        total_value = Decimal('0')
        for position in portfolio['positions']:
            quantity = position['quantity']
            current_price = position['current_price']
            total_value += quantity * current_price

        return {
            'timestamp': datetime.utcnow().isoformat(),
            'total_value': float(total_value),
            'positions': [
                {
                    'figi': pos['figi'],
                    'quantity': float(pos['quantity']),
                    'current_price': float(pos['current_price']),
                    'expected_yield': float(pos['expected_yield'])
                }
                for pos in portfolio['positions']
            ]
        }

    async def _calculate_changes(
        self,
        current: Dict,
        previous: Optional[Dict]
    ) -> Dict:
        """Calculate portfolio changes."""
        if not previous:
            return {
                'total_change_percent': 0,
                'position_changes': [],
                'significant_changes': False
            }

        # Изменение общей стоимости
        prev_value = previous['total_value']
        curr_value = current['total_value']
        total_change_percent = ((curr_value - prev_value) / prev_value) * 100

        # Изменения в позициях
        position_changes = []
        curr_positions = {pos['figi']: pos for pos in current['positions']}
        prev_positions = {pos['figi']: pos for pos in previous['positions']}

        # Проверяем все текущие позиции
        for figi, curr_pos in curr_positions.items():
            prev_pos = prev_positions.get(figi)
            if prev_pos:
                # Существующая позиция
                quantity_change = curr_pos['quantity'] - prev_pos['quantity']
                price_change_percent = ((curr_pos['current_price'] - prev_pos['current_price']) 
                                     / prev_pos['current_price'] * 100)
                
                if abs(quantity_change) > 0 or abs(price_change_percent) >= self.change_threshold:
                    position_changes.append({
                        'figi': figi,
                        'quantity_change': quantity_change,
                        'price_change_percent': price_change_percent
                    })
            else:
                # Новая позиция
                position_changes.append({
                    'figi': figi,
                    'quantity_change': curr_pos['quantity'],
                    'price_change_percent': 0
                })

        # Проверяем закрытые позиции
        for figi, prev_pos in prev_positions.items():
            if figi not in curr_positions:
                position_changes.append({
                    'figi': figi,
                    'quantity_change': -prev_pos['quantity'],
                    'price_change_percent': -100
                })

        return {
            'total_change_percent': total_change_percent,
            'position_changes': position_changes,
            'significant_changes': abs(total_change_percent) >= self.change_threshold or position_changes
        }

    async def _check_risk_alerts(self, snapshot: Dict) -> List[Dict]:
        """Check for risk management alerts."""
        alerts = []
        total_value = snapshot['total_value']

        for position in snapshot['positions']:
            position_value = position['quantity'] * position['current_price']
            position_weight = (position_value / total_value) * 100

            # Проверяем превышение веса позиции
            if position_weight > 20:  # Порог концентрации 20%
                alerts.append({
                    'type': 'concentration',
                    'figi': position['figi'],
                    'weight': position_weight
                })

            # Проверяем большие убытки
            if position['expected_yield'] < -10:  # Порог убытка 10%
                alerts.append({
                    'type': 'loss',
                    'figi': position['figi'],
                    'loss_percent': position['expected_yield']
                })

        return alerts

    async def _notify_changes(
        self,
        user_id: str,
        changes: Dict,
        risk_alerts: List[Dict]
    ):
        """Send notifications about portfolio changes."""
        # Уведомление об изменении стоимости портфеля
        if abs(changes['total_change_percent']) >= self.change_threshold:
            await self.notification_service.create_notification({
                'user_id': user_id,
                'type': NotificationType.PORTFOLIO_CHANGE,
                'title': 'Portfolio Value Change',
                'message': f'Your portfolio value has changed by {changes["total_change_percent"]:.1f}% in the last 5 minutes',
                'priority': NotificationPriority.HIGH if abs(changes['total_change_percent']) >= 10 else NotificationPriority.NORMAL,
                'metadata': {
                    'change_percent': changes['total_change_percent']
                }
            })

        # Уведомления об изменениях в позициях
        for change in changes['position_changes']:
            if abs(change['price_change_percent']) >= self.change_threshold:
                await self.notification_service.create_notification({
                    'user_id': user_id,
                    'type': NotificationType.PRICE_TARGET,
                    'title': 'Position Price Change',
                    'message': f'Position {change["figi"]} price changed by {change["price_change_percent"]:.1f}%',
                    'priority': NotificationPriority.NORMAL,
                    'metadata': change
                })

        # Уведомления о рисках
        for alert in risk_alerts:
            if alert['type'] == 'concentration':
                await self.notification_service.create_notification({
                    'user_id': user_id,
                    'type': NotificationType.RISK_ALERT,
                    'title': 'Position Concentration Risk',
                    'message': f'Position {alert["figi"]} weight ({alert["weight"]:.1f}%) exceeds 20% of portfolio',
                    'priority': NotificationPriority.HIGH,
                    'metadata': alert
                })
            elif alert['type'] == 'loss':
                await self.notification_service.create_notification({
                    'user_id': user_id,
                    'type': NotificationType.RISK_ALERT,
                    'title': 'Position Loss Alert',
                    'message': f'Position {alert["figi"]} is down {abs(alert["loss_percent"]):.1f}%',
                    'priority': NotificationPriority.HIGH,
                    'metadata': alert
                })

    async def monitor_user_portfolio(self, user_id: str):
        """Monitor portfolio for specific user."""
        try:
            # Получаем токен пользователя
            token = await self.token_service.get_token(user_id, 'tinkoff')
            if not token:
                logger.warning("No token found for user %s", user_id)
                return

            # Инициализируем клиент
            client = TinkoffClient(self.token_service, user_id)
            
            # Получаем список счетов
            accounts = await client.get_accounts()
            
            for account in accounts:
                # Получаем текущий снимок портфеля
                current_snapshot = await self._get_portfolio_snapshot(client, account['id'])
                
                # Получаем предыдущий снимок из кэша или базы
                previous_snapshot = await self._get_previous_snapshot(user_id, account['id'])
                
                # Рассчитываем изменения
                changes = await self._calculate_changes(current_snapshot, previous_snapshot)
                
                # Проверяем риски
                risk_alerts = await self._check_risk_alerts(current_snapshot)
                
                # Отправляем уведомления если есть значимые изменения
                if changes['significant_changes'] or risk_alerts:
                    await self._notify_changes(user_id, changes, risk_alerts)
                
                # Сохраняем текущий снимок
                await self._save_snapshot(user_id, account['id'], current_snapshot)
                
            logger.info("Completed portfolio monitoring for user %s", user_id)
        except Exception as e:
            logger.error("Error monitoring portfolio for user %s: %s", user_id, e)

    async def run(self):
        """Run portfolio monitoring for all users."""
        logger.info("Starting portfolio monitoring")
        try:
            # Получаем всех пользователей с активными токенами
            active_tokens = await self.token_service.get_all_active_tokens()
            
            for token in active_tokens:
                await self.monitor_user_portfolio(token['user_id'])
                
            logger.info("Portfolio monitoring completed")
        except Exception as e:
            logger.error("Error during portfolio monitoring: %s", e)

    async def _get_previous_snapshot(self, user_id: str, account_id: str) -> Optional[Dict]:
        """Get previous portfolio snapshot from database."""
        try:
            # Получаем последний снимок за последние 5 минут
            result = await self.token_service.supabase.table(self.snapshot_table) \
                .select('*') \
                .eq('user_id', user_id) \
                .eq('account_id', account_id) \
                .order('timestamp', desc=True) \
                .limit(1) \
                .execute()

            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.error("Error getting previous snapshot: %s", e)
            return None

    async def _save_snapshot(self, user_id: str, account_id: str, snapshot: Dict):
        """Save portfolio snapshot to database."""
        try:
            # Сохраняем снимок
            await self.token_service.supabase.table(self.snapshot_table).insert({
                'user_id': user_id,
                'account_id': account_id,
                'timestamp': snapshot['timestamp'],
                'total_value': snapshot['total_value'],
                'positions': snapshot['positions']
            }).execute()

            # Удаляем старые снимки (старше 24 часов)
            yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
            await self.token_service.supabase.table(self.snapshot_table) \
                .delete() \
                .lt('timestamp', yesterday) \
                .execute()
        except Exception as e:
            logger.error("Error saving snapshot: %s", e)

async def run(token_service: TokenService, notification_service: NotificationService, config: Dict):
    """Entry point for the background task."""
    monitor = PortfolioMonitor(token_service, notification_service, config)
    await monitor.run() 