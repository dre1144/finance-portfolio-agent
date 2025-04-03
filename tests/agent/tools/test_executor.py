import pytest
from src.models.base import Tool, ToolType, Message
from src.agent.tools.executor import ToolExecutor
from src.agent.tools.base import BaseTool


class SuccessfulTool(BaseTool):
    """Tool that successfully returns test data."""
    
    async def execute(self, message, context):
        return {"success": True, "data": "test"}


class FailingTool(BaseTool):
    """Tool that raises an exception."""
    
    async def execute(self, message, context):
        raise ValueError("Test error")


@pytest.fixture
def executor():
    """Create ToolExecutor instance."""
    return ToolExecutor()


@pytest.fixture
def successful_tool_config():
    """Create configuration for successful tool."""
    return Tool(
        name="successful_tool",
        type=ToolType.ANALYSIS,
        description="Test tool",
        parameters={},
        required_parameters=[]
    )


@pytest.fixture
def failing_tool_config():
    """Create configuration for failing tool."""
    return Tool(
        name="failing_tool",
        type=ToolType.ANALYSIS,
        description="Test tool",
        parameters={},
        required_parameters=[]
    )


def test_register_implementation(executor):
    """Test registering tool implementation."""
    executor.register_implementation("test_tool", SuccessfulTool)
    assert "test_tool" in executor._tool_implementations


def test_get_tool_instance_missing(executor, successful_tool_config):
    """Test getting instance of unregistered tool."""
    with pytest.raises(ValueError, match="No implementation found"):
        executor.get_tool_instance(successful_tool_config)


def test_get_tool_instance_cached(executor, successful_tool_config):
    """Test that tool instances are cached."""
    executor.register_implementation(successful_tool_config.name, SuccessfulTool)
    
    instance1 = executor.get_tool_instance(successful_tool_config)
    instance2 = executor.get_tool_instance(successful_tool_config)
    
    assert instance1 is instance2


async def test_execute_tool_success(executor, successful_tool_config):
    """Test successful tool execution."""
    executor.register_implementation(successful_tool_config.name, SuccessfulTool)
    
    message = Message(content="test", role="user")
    result = await executor.execute_tool(successful_tool_config, message, {})
    
    assert result["status"] == "success"
    assert result["tool"] == successful_tool_config.name
    assert "result" in result


async def test_execute_tool_failure(executor, failing_tool_config):
    """Test handling of tool execution failure."""
    executor.register_implementation(failing_tool_config.name, FailingTool)
    
    message = Message(content="test", role="user")
    result = await executor.execute_tool(failing_tool_config, message, {})
    
    assert result["status"] == "error"
    assert result["tool"] == failing_tool_config.name
    assert "Test error" in result["error"]


async def test_execute_tools_sequence(executor, successful_tool_config, failing_tool_config):
    """Test executing multiple tools in sequence."""
    executor.register_implementation(successful_tool_config.name, SuccessfulTool)
    executor.register_implementation(failing_tool_config.name, FailingTool)
    
    message = Message(content="test", role="user")
    tools = [successful_tool_config, failing_tool_config]
    
    results = await executor.execute_tools(tools, message, {})
    
    assert len(results) == 2
    assert results[0]["status"] == "success"
    assert results[1]["status"] == "error"


async def test_execute_tools_context_passing(executor, successful_tool_config):
    """Test that tool results are added to context."""
    executor.register_implementation(successful_tool_config.name, SuccessfulTool)
    
    message = Message(content="test", role="user")
    context = {}
    
    await executor.execute_tools([successful_tool_config], message, context)
    
    assert f"tool_result_{successful_tool_config.name}" in context 