"""
Notification service using Supabase Realtime.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Union
from enum import Enum

from supabase import create_client, Client

logger = logging.getLogger(__name__)

class NotificationType(Enum):
    TOKEN_INVALID = 'token_invalid'
    PORTFOLIO_CHANGE = 'portfolio_change'
    PRICE_TARGET = 'price_target'
    CORPORATE_EVENT = 'corporate_event'
    RISK_ALERT = 'risk_alert'
    REBALANCE_SUGGESTION = 'rebalance_suggestion'

class NotificationPriority(Enum):
    LOW = 'low'
    NORMAL = 'normal'
    HIGH = 'high'
    URGENT = 'urgent'

class NotificationService:
    """Service for managing notifications in Supabase with Realtime support."""

    def __init__(self, supabase_url: str, supabase_key: str):
        """Initialize service with Supabase credentials."""
        self.supabase: Client = create_client(supabase_url, supabase_key)
        logger.info("Initialized NotificationService")

    async def create_notification(self, notification: Dict) -> bool:
        """
        Create a new notification.
        
        Args:
            notification: Dictionary containing:
                - user_id: str
                - type: NotificationType
                - title: str
                - message: str
                - priority: NotificationPriority (optional)
                - metadata: Dict (optional)
        """
        try:
            # Проверяем тип уведомления
            if isinstance(notification['type'], NotificationType):
                notification_type = notification['type'].value
            else:
                notification_type = notification['type']

            # Проверяем приоритет
            priority = notification.get('priority', NotificationPriority.NORMAL)
            if isinstance(priority, NotificationPriority):
                priority = priority.value

            # Формируем данные для вставки
            notification_data = {
                'user_id': notification['user_id'],
                'type': notification_type,
                'title': notification['title'],
                'message': notification['message'],
                'priority': priority,
                'metadata': notification.get('metadata', {}),
                'created_at': datetime.utcnow().isoformat(),
                'is_read': False,
                'is_dismissed': False
            }

            # Создаем уведомление
            result = await self.supabase.table('notifications') \
                .insert(notification_data) \
                .execute()

            return bool(result.data)
        except Exception as e:
            logger.error("Error creating notification: %s", e)
            return False

    async def mark_as_read(self, user_id: str, notification_id: str) -> bool:
        """Mark notification as read."""
        try:
            result = await self.supabase.table('notifications') \
                .update({
                    'is_read': True,
                    'read_at': datetime.utcnow().isoformat()
                }) \
                .eq('id', notification_id) \
                .eq('user_id', user_id) \
                .execute()
            return bool(result.data)
        except Exception as e:
            logger.error("Error marking notification as read: %s", e)
            return False

    async def dismiss_notification(self, user_id: str, notification_id: str) -> bool:
        """Dismiss notification."""
        try:
            result = await self.supabase.table('notifications') \
                .update({'is_dismissed': True}) \
                .eq('id', notification_id) \
                .eq('user_id', user_id) \
                .execute()
            return bool(result.data)
        except Exception as e:
            logger.error("Error dismissing notification: %s", e)
            return False

    async def get_user_notifications(
        self,
        user_id: str,
        include_read: bool = False,
        include_dismissed: bool = False,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict]:
        """Get user notifications with filters."""
        try:
            query = self.supabase.table('notifications') \
                .select('*') \
                .eq('user_id', user_id)

            if not include_read:
                query = query.eq('is_read', False)
            if not include_dismissed:
                query = query.eq('is_dismissed', False)

            query = query.order('created_at', desc=True) \
                .range(offset, offset + limit - 1)

            result = await query.execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error("Error getting notifications: %s", e)
            return []

    async def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications."""
        try:
            result = await self.supabase.table('notifications') \
                .select('*', count='exact') \
                .eq('user_id', user_id) \
                .eq('is_read', False) \
                .eq('is_dismissed', False) \
                .execute()
            return result.count if result.count is not None else 0
        except Exception as e:
            logger.error("Error getting unread count: %s", e)
            return 0

    async def delete_old_notifications(self, days: int = 30) -> bool:
        """Delete notifications older than specified days."""
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            result = await self.supabase.table('notifications') \
                .delete() \
                .lt('created_at', cutoff_date) \
                .execute()
            return bool(result.data)
        except Exception as e:
            logger.error("Error deleting old notifications: %s", e)
            return False

    async def subscribe_to_notifications(self, user_id: str, callback) -> None:
        """
        Subscribe to real-time notifications.
        
        Args:
            user_id: User ID to subscribe for
            callback: Async function to call when notification is received
        """
        try:
            # Подписываемся на изменения в таблице notifications для конкретного пользователя
            self.supabase.table('notifications') \
                .on('INSERT', lambda payload: callback(payload)) \
                .subscribe()
            
            logger.info("Subscribed to notifications for user %s", user_id)
        except Exception as e:
            logger.error("Error subscribing to notifications: %s", e)
            raise 