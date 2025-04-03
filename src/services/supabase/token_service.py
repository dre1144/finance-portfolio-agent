"""
Token management service using Supabase.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict

from supabase import create_client, Client

logger = logging.getLogger(__name__)

class TokenService:
    """Service for managing broker tokens in Supabase."""

    def __init__(self, supabase_url: str, supabase_key: str, encryption_key: str):
        """Initialize service with Supabase credentials."""
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.encryption_key = encryption_key
        logger.info("Initialized TokenService")

    async def save_token(self, user_id: str, broker_type: str, token: str) -> bool:
        """Save or update broker token."""
        try:
            # Шифруем токен через RPC функцию в Supabase
            encrypted = await self.supabase.rpc(
                'encrypt_token',
                {'token': token, 'key': self.encryption_key}
            ).execute()

            if not encrypted.data:
                logger.error("Failed to encrypt token")
                return False

            # Проверяем существование токена
            existing = await self.supabase.table('user_tokens') \
                .select('id') \
                .eq('user_id', user_id) \
                .eq('broker_type', broker_type) \
                .execute()

            if existing.data:
                # Обновляем существующий токен
                result = await self.supabase.table('user_tokens') \
                    .update({
                        'encrypted_token': encrypted.data,
                        'is_active': True,
                        'last_validated_at': datetime.utcnow().isoformat()
                    }) \
                    .eq('user_id', user_id) \
                    .eq('broker_type', broker_type) \
                    .execute()
            else:
                # Создаем новую запись
                result = await self.supabase.table('user_tokens') \
                    .insert({
                        'user_id': user_id,
                        'broker_type': broker_type,
                        'encrypted_token': encrypted.data,
                        'last_validated_at': datetime.utcnow().isoformat()
                    }) \
                    .execute()

            return bool(result.data)
        except Exception as e:
            logger.error("Error saving token: %s", e)
            return False

    async def get_token(self, user_id: str, broker_type: str) -> Optional[str]:
        """Get decrypted broker token."""
        try:
            # Получаем зашифрованный токен
            result = await self.supabase.table('user_tokens') \
                .select('encrypted_token') \
                .eq('user_id', user_id) \
                .eq('broker_type', broker_type) \
                .eq('is_active', True) \
                .execute()

            if not result.data:
                return None

            encrypted_token = result.data[0]['encrypted_token']

            # Расшифровываем токен через RPC функцию
            decrypted = await self.supabase.rpc(
                'decrypt_token',
                {'encrypted_token': encrypted_token, 'key': self.encryption_key}
            ).execute()

            return decrypted.data if decrypted.data else None
        except Exception as e:
            logger.error("Error getting token: %s", e)
            return None

    async def get_all_active_tokens(self) -> List[Dict]:
        """Get all active tokens."""
        try:
            result = await self.supabase.table('user_tokens') \
                .select('user_id,broker_type,last_validated_at') \
                .eq('is_active', True) \
                .execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error("Error getting active tokens: %s", e)
            return []

    async def invalidate_token(self, user_id: str, broker_type: str) -> bool:
        """Mark token as inactive."""
        try:
            result = await self.supabase.table('user_tokens') \
                .update({'is_active': False}) \
                .eq('user_id', user_id) \
                .eq('broker_type', broker_type) \
                .execute()
            return bool(result.data)
        except Exception as e:
            logger.error("Error invalidating token: %s", e)
            return False

    async def validate_token(self, user_id: str, broker_type: str) -> bool:
        """Update last validation timestamp."""
        try:
            result = await self.supabase.table('user_tokens') \
                .update({'last_validated_at': datetime.utcnow().isoformat()}) \
                .eq('user_id', user_id) \
                .eq('broker_type', broker_type) \
                .execute()
            return bool(result.data)
        except Exception as e:
            logger.error("Error updating token validation: %s", e)
            return False 