from typing import Dict, List, Optional, Any
import json
from redis import Redis
from src.models.base import Context, Message, Tool


class AgentContext:
    """Менеджер контекста для MCP агента"""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self._context: Optional[Context] = None

    @property
    def context(self) -> Context:
        """Получение текущего контекста"""
        if self._context is None:
            self._context = Context()
        return self._context

    def add_message(self, message: Message) -> None:
        """Добавление сообщения в контекст"""
        self.context.messages.append(message)
        self._save_context()

    def add_tool(self, tool: Tool) -> None:
        """Регистрация инструмента в контексте"""
        self.context.tools.append(tool)
        self._save_context()

    def update_metadata(self, key: str, value: Any) -> None:
        """Обновление метаданных контекста"""
        self.context.metadata[key] = value
        self._save_context()

    def get_conversation_history(self, limit: Optional[int] = None) -> List[Message]:
        """Получение истории сообщений"""
        messages = self.context.messages
        if limit:
            messages = messages[-limit:]
        return messages

    def get_tool_by_name(self, name: str) -> Optional[Tool]:
        """Поиск инструмента по имени"""
        for tool in self.context.tools:
            if tool.name == name:
                return tool
        return None

    def _save_context(self) -> None:
        """Сохранение контекста в Redis"""
        if self._context:
            context_data = self._context.json()
            self.redis.set("mcp:context", context_data)

    def load_context(self) -> None:
        """Загрузка контекста из Redis"""
        context_data = self.redis.get("mcp:context")
        if context_data:
            self._context = Context.parse_raw(context_data)
        else:
            self._context = Context()

    def clear_context(self) -> None:
        """Очистка контекста"""
        self._context = Context()
        self.redis.delete("mcp:context") 