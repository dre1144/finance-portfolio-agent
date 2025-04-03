"""Notification service using Supabase."""

import logging
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional

from supabase import Client

logger = logging.getLogger(__name__)

class NotificationType(Enum):
    """Types of notifications."""
    PORTFOLIO_CHANGE = auto()
    PRICE_TARGET = auto()
    RISK_ALERT = auto()
    TOKEN_INVALID = auto()

class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()
    URGENT = auto()

class NotificationService:
    """Service for managing notifications."""

    def __init__(self, supabase: Client):
        """Initialize service with Supabase client."""
        self.supabase = supabase
        self.table = 'notifications'
        logger.info("Initialized NotificationService")

    async def create_notification(self, notification: Dict) -> Dict:
        """Create a new notification."""
        try:
            # Добавляем timestamp
            notification['created_at'] = datetime.utcnow().isoformat()
            notification['read'] = False
            notification['dismissed'] = False

            # Сохраняем уведомление
            result = await self.supabase.table(self.table).insert(notification).execute()
            
            # Отправляем realtime событие
            await self.supabase.rpc(
                'broadcast_notification',
                {
                    'p_user_id': notification['user_id'],
                    'p_notification': result.data[0]
                }
            ).execute()

            return result.data[0]
        except Exception as e:
            logger.error("Error creating notification: %s", e)
            raise

    async def mark_as_read(self, user_id: str, notification_id: str) -> bool:
        """Mark notification as read."""
        try:
            await self.supabase.table(self.table) \
                .update({'read': True}) \
                .eq('id', notification_id) \
                .eq('user_id', user_id) \
                .execute()
            return True
        except Exception as e:
            logger.error("Error marking notification as read: %s", e)
            return False

    async def dismiss_notification(self, user_id: str, notification_id: str) -> bool:
        """Dismiss notification."""
        try:
            await self.supabase.table(self.table) \
                .update({'dismissed': True}) \
                .eq('id', notification_id) \
                .eq('user_id', user_id) \
                .execute()
            return True
        except Exception as e:
            logger.error("Error dismissing notification: %s", e)
            return False

    async def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """Get user notifications with filters."""
        try:
            query = self.supabase.table(self.table) \
                .select('*') \
                .eq('user_id', user_id) \
                .eq('dismissed', False)

            if unread_only:
                query = query.eq('read', False)

            result = await query \
                .order('created_at', desc=True) \
                .limit(limit) \
                .offset(offset) \
                .execute()

            return result.data
        except Exception as e:
            logger.error("Error getting notifications: %s", e)
            return []

    async def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications."""
        try:
            result = await self.supabase.rpc(
                'count_unread_notifications',
                {'p_user_id': user_id}
            ).execute()
            return result.data
        except Exception as e:
            logger.error("Error getting unread count: %s", e)
            return 0

    async def delete_old_notifications(self, days: int = 30) -> bool:
        """Delete notifications older than specified days."""
        try:
            await self.supabase.rpc(
                'delete_old_notifications',
                {'p_days': days}
            ).execute()
            return True
        except Exception as e:
            logger.error("Error deleting old notifications: %s", e)
            return False

    async def subscribe_to_notifications(self, user_id: str, callback) -> None:
        """Subscribe to real-time notifications."""
        try:
            await self.supabase \
                .channel('notifications') \
                .on(
                    'postgres_changes',
                    {
                        'event': 'INSERT',
                        'schema': 'public',
                        'table': self.table,
                        'filter': f"user_id=eq.{user_id}"
                    },
                    callback
                ) \
                .subscribe()
        except Exception as e:
            logger.error("Error subscribing to notifications: %s", e) 