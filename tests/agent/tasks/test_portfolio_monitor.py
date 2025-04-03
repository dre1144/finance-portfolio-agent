"""Tests for portfolio monitoring task."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from src.agent.tasks.portfolio_monitor import PortfolioMonitor
from src.services.supabase.notification_service import NotificationType, NotificationPriority

@pytest.fixture
def token_service():
    """Mock token service."""
    service = AsyncMock()
    service.supabase = AsyncMock()
    return service

@pytest.fixture
def notification_service():
    """Mock notification service."""
    return AsyncMock()

@pytest.fixture
def config():
    """Test config."""
    return {
        'change_threshold': 5.0
    }

@pytest.fixture
def monitor(token_service, notification_service, config):
    """Create portfolio monitor instance."""
    return PortfolioMonitor(token_service, notification_service, config)

@pytest.fixture
def portfolio_snapshot():
    """Sample portfolio snapshot."""
    return {
        'timestamp': datetime.utcnow().isoformat(),
        'total_value': 1000000.0,
        'positions': [
            {
                'figi': 'BBG000B9XRY4',
                'quantity': 100.0,
                'current_price': 150.0,
                'expected_yield': 15.0
            },
            {
                'figi': 'BBG000BVPV84',
                'quantity': 200.0,
                'current_price': 75.0,
                'expected_yield': -12.0
            }
        ]
    }

@pytest.mark.asyncio
async def test_get_portfolio_snapshot(monitor):
    """Test getting portfolio snapshot."""
    client = AsyncMock()
    client.get_portfolio.return_value = {
        'positions': [
            {
                'figi': 'BBG000B9XRY4',
                'quantity': 100,
                'current_price': 150,
                'expected_yield': 15.0
            }
        ]
    }
    
    snapshot = await monitor._get_portfolio_snapshot(client, 'test_account')
    
    assert snapshot['total_value'] == 15000.0
    assert len(snapshot['positions']) == 1
    assert snapshot['positions'][0]['figi'] == 'BBG000B9XRY4'
    assert snapshot['positions'][0]['quantity'] == 100.0

@pytest.mark.asyncio
async def test_calculate_changes_new_portfolio(monitor, portfolio_snapshot):
    """Test calculating changes for new portfolio."""
    changes = await monitor._calculate_changes(portfolio_snapshot, None)
    
    assert changes['total_change_percent'] == 0
    assert len(changes['position_changes']) == 0
    assert not changes['significant_changes']

@pytest.mark.asyncio
async def test_calculate_changes_with_significant_change(monitor, portfolio_snapshot):
    """Test calculating changes with significant price change."""
    previous = portfolio_snapshot.copy()
    previous['total_value'] = 900000.0
    
    changes = await monitor._calculate_changes(portfolio_snapshot, previous)
    
    assert changes['total_change_percent'] == pytest.approx(11.11, rel=1e-2)
    assert changes['significant_changes']

@pytest.mark.asyncio
async def test_check_risk_alerts(monitor, portfolio_snapshot):
    """Test checking risk alerts."""
    alerts = await monitor._check_risk_alerts(portfolio_snapshot)
    
    # Проверяем алерт по убытку
    loss_alert = next(alert for alert in alerts if alert['type'] == 'loss')
    assert loss_alert['figi'] == 'BBG000BVPV84'
    assert loss_alert['loss_percent'] == -12.0

@pytest.mark.asyncio
async def test_notify_changes(monitor, portfolio_snapshot):
    """Test sending notifications."""
    changes = {
        'total_change_percent': 6.0,
        'position_changes': [
            {
                'figi': 'BBG000B9XRY4',
                'quantity_change': 0,
                'price_change_percent': 7.0
            }
        ],
        'significant_changes': True
    }
    
    risk_alerts = [
        {
            'type': 'loss',
            'figi': 'BBG000BVPV84',
            'loss_percent': -12.0
        }
    ]
    
    await monitor._notify_changes('test_user', changes, risk_alerts)
    
    # Проверяем, что были отправлены нужные уведомления
    calls = monitor.notification_service.create_notification.call_args_list
    assert len(calls) == 3  # Portfolio change + position change + risk alert
    
    # Проверяем уведомление об изменении портфеля
    portfolio_notification = calls[0].args[0]
    assert portfolio_notification['type'] == NotificationType.PORTFOLIO_CHANGE
    assert portfolio_notification['priority'] == NotificationPriority.NORMAL

@pytest.mark.asyncio
async def test_monitor_user_portfolio(monitor, portfolio_snapshot):
    """Test monitoring user portfolio."""
    # Настраиваем моки
    monitor.token_service.get_token.return_value = 'test_token'
    
    client = AsyncMock()
    client.get_accounts.return_value = [{'id': 'test_account'}]
    client.get_portfolio.return_value = {
        'positions': portfolio_snapshot['positions']
    }
    
    with patch('src.agent.tasks.portfolio_monitor.TinkoffClient', return_value=client):
        await monitor.monitor_user_portfolio('test_user')
    
    # Проверяем, что снимок был сохранен
    assert monitor.token_service.supabase.table.call_args.args[0] == 'portfolio_snapshots'

@pytest.mark.asyncio
async def test_run(monitor):
    """Test running the monitoring task."""
    # Настраиваем моки
    monitor.token_service.get_all_active_tokens.return_value = [
        {'user_id': 'test_user1'},
        {'user_id': 'test_user2'}
    ]
    
    monitor.monitor_user_portfolio = AsyncMock()
    
    await monitor.run()
    
    # Проверяем, что мониторинг был запущен для каждого пользователя
    assert monitor.monitor_user_portfolio.call_count == 2
    monitor.monitor_user_portfolio.assert_any_call('test_user1')
    monitor.monitor_user_portfolio.assert_any_call('test_user2') 