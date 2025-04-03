import pytest
from redis import Redis
from unittest.mock import MagicMock
from src.models.base import Message, Tool, ToolType
from src.agent.context import AgentContext


@pytest.fixture
def redis_mock():
    """Mock Redis client for testing."""
    redis = MagicMock(spec=Redis)
    redis.get.return_value = None
    return redis


@pytest.fixture
def agent_context(redis_mock):
    """Create AgentContext instance with mocked Redis."""
    return AgentContext(redis_mock)


@pytest.fixture
def sample_message():
    """Create sample message for testing."""
    return Message(content="Test message", role="user")


@pytest.fixture
def sample_tool():
    """Create sample tool for testing."""
    return Tool(
        name="test_tool",
        type=ToolType.ANALYSIS,
        description="Test tool",
        parameters={"param1": "string"},
        required_parameters=["param1"]
    ) 