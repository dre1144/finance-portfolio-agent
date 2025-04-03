"""
Background task for validating broker tokens.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict

from ...services.supabase.token_service import TokenService
from ...services.tinkoff.client import TinkoffClient
from ...services.supabase.notification_service import NotificationService

logger = logging.getLogger(__name__)

class TokenValidator:
    """Token validation task."""

    def __init__(
        self,
        token_service: TokenService,
        notification_service: NotificationService,
        config: Dict
    ):
        """Initialize validator with services and config."""
        self.token_service = token_service
        self.notification_service = notification_service
        self.config = config
        self.retry_attempts = config.get('retry_attempts', 3)
        self.retry_delay = config.get('retry_delay', 300)  # 5 минут
        logger.info("Initialized TokenValidator")

    async def _validate_token(self, user_id: str, broker_type: str) -> bool:
        """Validate single token with retries."""
        attempts = 0
        while attempts < self.retry_attempts:
            try:
                if broker_type == 'tinkoff':
                    client = TinkoffClient(self.token_service, user_id)
                    is_valid = await client.validate_token()
                    if is_valid:
                        await self.token_service.validate_token(user_id, broker_type)
                        return True
                    else:
                        await self.token_service.invalidate_token(user_id, broker_type)
                        return False
            except Exception as e:
                logger.error("Error validating token: %s", e)
                attempts += 1
                if attempts < self.retry_attempts:
                    await asyncio.sleep(self.retry_delay)
                continue
        return False

    async def _notify_user(self, user_id: str, broker_type: str, is_valid: bool):
        """Send notification about token status."""
        if not is_valid:
            await self.notification_service.create_notification({
                'user_id': user_id,
                'type': 'token_invalid',
                'title': 'Broker Token Invalid',
                'message': f'Your {broker_type} token is no longer valid. Please update it to continue receiving portfolio updates.',
                'priority': 'high'
            })

    async def run(self):
        """Run token validation for all tokens."""
        logger.info("Starting token validation")
        try:
            # Получаем все активные токены
            tokens = await self.token_service.get_all_active_tokens()
            
            for token in tokens:
                user_id = token['user_id']
                broker_type = token['broker_type']
                
                # Проверяем токен
                is_valid = await self._validate_token(user_id, broker_type)
                
                # Отправляем уведомление если токен невалиден
                await self._notify_user(user_id, broker_type, is_valid)
                
                # Небольшая пауза между проверками
                await asyncio.sleep(1)
                
            logger.info("Token validation completed")
        except Exception as e:
            logger.error("Error during token validation: %s", e)

async def run(token_service: TokenService, notification_service: NotificationService, config: Dict):
    """Entry point for the background task."""
    validator = TokenValidator(token_service, notification_service, config)
    await validator.run() 