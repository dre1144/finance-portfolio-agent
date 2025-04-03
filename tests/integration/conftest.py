import pytest
from redis import Redis
from unittest.mock import MagicMock
from src.models.base import Tool, ToolType, Message
from src.agent.context import AgentContext
from src.agent.tools.registry import ToolRegistry
from src.agent.tools.executor import ToolExecutor
from src.agent.message_handler import MessageHandler
from src.agent.tools.base import BaseTool


class PortfolioTool(BaseTool):
    """Test portfolio tool implementation."""
    
    async def execute(self, message: Message, context: dict) -> dict:
        return {
            "total_value": 100000.0,
            "currency": "RUB",
            "positions": [
                {"ticker": "AAPL", "quantity": 10, "price": 180.0},
                {"ticker": "GOOGL", "quantity": 5, "price": 140.0}
            ]
        }


class AnalysisTool(BaseTool):
    """Test analysis tool implementation."""
    
    async def execute(self, message: Message, context: dict) -> dict:
        return {
            "risk_level": "moderate",
            "volatility": 0.15,
            "sharpe_ratio": 1.2
        }


@pytest.fixture
def redis_mock():
    """Create Redis mock."""
    redis = MagicMock(spec=Redis)
    redis.get.return_value = None
    return redis


@pytest.fixture
def agent_context(redis_mock):
    """Create AgentContext instance."""
    return AgentContext(redis_mock)


@pytest.fixture
def tool_registry():
    """Create ToolRegistry instance."""
    return ToolRegistry()


@pytest.fixture
def tool_executor():
    """Create ToolExecutor instance with test tools."""
    executor = ToolExecutor()
    
    # Register test tools
    executor.register_implementation("portfolio", PortfolioTool)
    executor.register_implementation("analysis", AnalysisTool)
    
    return executor


@pytest.fixture
def portfolio_tool():
    """Create portfolio tool configuration."""
    return Tool(
        name="portfolio",
        type=ToolType.PORTFOLIO,
        description="Get portfolio information",
        parameters={},
        required_parameters=[]
    )


@pytest.fixture
def analysis_tool():
    """Create analysis tool configuration."""
    return Tool(
        name="analysis",
        type=ToolType.ANALYSIS,
        description="Analyze portfolio",
        parameters={},
        required_parameters=[]
    )


@pytest.fixture
def message_handler(agent_context, tool_registry, tool_executor):
    """Create MessageHandler instance with all dependencies."""
    return MessageHandler(agent_context, tool_registry, tool_executor) 