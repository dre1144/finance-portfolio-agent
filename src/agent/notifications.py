from typing import List, Dict, Any
import logging
from datetime import datetime
from supabase import create_client, Client
import os

logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self):
        self.supabase: Client = create_client(
            supabase_url=os.getenv('SUPABASE_URL'),
            supabase_key=os.getenv('SUPABASE_SERVICE_KEY')
        )

    async def send_notification(
        self,
        user_id: str,
        alerts: List[Dict[str, Any]],
        portfolio_data: Dict[str, Any]
    ) -> None:
        """
        Отправляет уведомление пользователю через Supabase Realtime
        """
        try:
            # Создаем запись в таблице уведомлений
            notification = {
                'user_id': user_id,
                'type': 'portfolio_alert',
                'status': 'unread',
                'created_at': datetime.utcnow().isoformat(),
                'data': {
                    'alerts': alerts,
                    'portfolio': portfolio_data
                }
            }
            
            # Сохраняем уведомление
            result = await self.supabase.table('notifications').insert(notification).execute()
            
            if not result.data:
                raise Exception("Failed to save notification")
                
            # Отправляем событие через Realtime
            await self.supabase.rpc(
                'broadcast_notification',
                {
                    'p_user_id': user_id,
                    'p_notification_id': result.data[0]['id']
                }
            ).execute()
            
            logger.info(f"Notification sent to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error sending notification to user {user_id}: {str(e)}")
            raise

# Создаем глобальный экземпляр
notification_manager = NotificationManager()

async def send_notification(
    user_id: str,
    alerts: List[Dict[str, Any]],
    portfolio_data: Dict[str, Any]
) -> None:
    """
    Удобная функция для отправки уведомлений
    """
    await notification_manager.send_notification(
        user_id=user_id,
        alerts=alerts,
        portfolio_data=portfolio_data
    ) 