from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolType(str, Enum):
    """Типы инструментов, доступных агенту"""
    PORTFOLIO = "portfolio"
    MARKET_DATA = "market_data"
    ANALYSIS = "analysis"
    RECOMMENDATION = "recommendation"


class Tool(BaseModel):
    """Базовая модель инструмента"""
    name: str
    type: ToolType
    description: str
    parameters: Dict[str, Any]
    required_parameters: List[str]


class Message(BaseModel):
    """Базовая модель сообщения в MCP протоколе"""
    content: str
    role: str = Field(default="user")
    metadata: Optional[Dict[str, Any]] = None


class Context(BaseModel):
    """Контекст взаимодействия с агентом"""
    messages: List[Message] = Field(default_factory=list)
    tools: List[Tool] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """Ответ агента"""
    message: Message
    context: Context
    tool_calls: Optional[List[Dict[str, Any]]] = None 