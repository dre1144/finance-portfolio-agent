import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.agent.context import AgentContext
from src.agent.tools.base import BaseTool
from src.services.tinkoff.client import TinkoffClient

class MockTool(BaseTool):
    """Mock tool for testing."""
    def __init__(self, name: str, return_value: any):
        self.name = name
        self.return_value = return_value
        self.called_with = None
    
    def execute(self, **kwargs):
        self.called_with = kwargs
        return self.return_value

@pytest.fixture
def mock_tinkoff_client():
    """Create mock Tinkoff client."""
    return Mock(spec=TinkoffClient)

@pytest.fixture
def agent_context(mock_tinkoff_client):
    """Create agent context with mock client."""
    context = AgentContext(tinkoff_client=mock_tinkoff_client)
    return context

def test_context_initialization(agent_context):
    """Test agent context initialization."""
    assert agent_context.tinkoff_client is not None
    assert agent_context.tools == {}
    assert agent_context.conversation_history == []

def test_tool_registration(agent_context):
    """Test tool registration in context."""
    mock_tool = MockTool("test_tool", return_value={"status": "success"})
    agent_context.register_tool(mock_tool)
    
    assert "test_tool" in agent_context.tools
    assert agent_context.tools["test_tool"] == mock_tool

def test_tool_execution(agent_context):
    """Test tool execution through context."""
    mock_tool = MockTool("test_tool", return_value={"status": "success"})
    agent_context.register_tool(mock_tool)
    
    result = agent_context.execute_tool("test_tool", param1="value1", param2="value2")
    
    assert result == {"status": "success"}
    assert mock_tool.called_with == {"param1": "value1", "param2": "value2"}

def test_conversation_history(agent_context):
    """Test conversation history management."""
    user_message = {
        "role": "user",
        "content": "Test message",
        "timestamp": datetime.now()
    }
    agent_message = {
        "role": "assistant",
        "content": "Test response",
        "timestamp": datetime.now()
    }
    
    agent_context.add_to_history(user_message)
    agent_context.add_to_history(agent_message)
    
    assert len(agent_context.conversation_history) == 2
    assert agent_context.conversation_history[0] == user_message
    assert agent_context.conversation_history[1] == agent_message

def test_context_state_management(agent_context):
    """Test context state management."""
    # Set some state
    agent_context.set_state("current_portfolio", {"total": 1000})
    agent_context.set_state("risk_profile", "moderate")
    
    # Get state
    assert agent_context.get_state("current_portfolio") == {"total": 1000}
    assert agent_context.get_state("risk_profile") == "moderate"
    
    # Update state
    agent_context.set_state("current_portfolio", {"total": 1500})
    assert agent_context.get_state("current_portfolio") == {"total": 1500}
    
    # Clear state
    agent_context.clear_state("risk_profile")
    assert agent_context.get_state("risk_profile") is None

@pytest.mark.asyncio
async def test_async_tool_execution(agent_context):
    """Test asynchronous tool execution."""
    class AsyncMockTool(BaseTool):
        async def execute(self, **kwargs):
            return {"status": "async success"}
    
    mock_tool = AsyncMockTool("async_test_tool")
    agent_context.register_tool(mock_tool)
    
    result = await agent_context.execute_tool_async("async_test_tool")
    assert result == {"status": "async success"}

def test_error_handling(agent_context):
    """Test error handling in tool execution."""
    class ErrorTool(BaseTool):
        def execute(self, **kwargs):
            raise ValueError("Test error")
    
    error_tool = ErrorTool("error_tool")
    agent_context.register_tool(error_tool)
    
    with pytest.raises(ValueError) as exc_info:
        agent_context.execute_tool("error_tool")
    assert str(exc_info.value) == "Test error"

def test_tool_validation(agent_context):
    """Test tool parameter validation."""
    class ValidatedTool(BaseTool):
        def validate_params(self, **kwargs):
            if "required_param" not in kwargs:
                raise ValueError("required_param is missing")
            if not isinstance(kwargs["required_param"], str):
                raise TypeError("required_param must be a string")
        
        def execute(self, **kwargs):
            return {"status": "validated"}
    
    validated_tool = ValidatedTool("validated_tool")
    agent_context.register_tool(validated_tool)
    
    # Test missing parameter
    with pytest.raises(ValueError) as exc_info:
        agent_context.execute_tool("validated_tool")
    assert str(exc_info.value) == "required_param is missing"
    
    # Test invalid parameter type
    with pytest.raises(TypeError) as exc_info:
        agent_context.execute_tool("validated_tool", required_param=123)
    assert str(exc_info.value) == "required_param must be a string"
    
    # Test valid parameters
    result = agent_context.execute_tool("validated_tool", required_param="valid")
    assert result == {"status": "validated"}

def test_context_cleanup(agent_context):
    """Test context cleanup and resource management."""
    # Add some state and history
    agent_context.set_state("test_state", "value")
    agent_context.add_to_history({"role": "user", "content": "test"})
    
    # Register a tool with cleanup needs
    class CleanupTool(BaseTool):
        def __init__(self, name: str):
            self.name = name
            self.cleaned_up = False
        
        def cleanup(self):
            self.cleaned_up = True
    
    cleanup_tool = CleanupTool("cleanup_tool")
    agent_context.register_tool(cleanup_tool)
    
    # Perform cleanup
    agent_context.cleanup()
    
    # Verify cleanup results
    assert len(agent_context.conversation_history) == 0
    assert len(agent_context.get_all_state()) == 0
    assert cleanup_tool.cleaned_up == True

def test_tool_dependencies(agent_context):
    """Test tool dependency management."""
    # Create tools with dependencies
    class DependentTool(BaseTool):
        def __init__(self, name: str, dependencies: list):
            self.name = name
            self.dependencies = dependencies
        
        def get_dependencies(self):
            return self.dependencies
        
        def execute(self, **kwargs):
            return {"status": "executed", "dependencies": self.dependencies}
    
    tool_a = DependentTool("tool_a", [])
    tool_b = DependentTool("tool_b", ["tool_a"])
    tool_c = DependentTool("tool_c", ["tool_b"])
    
    # Register tools
    agent_context.register_tool(tool_a)
    agent_context.register_tool(tool_b)
    agent_context.register_tool(tool_c)
    
    # Verify dependency resolution
    assert agent_context.get_tool_dependencies("tool_c") == ["tool_b", "tool_a"]
    assert agent_context.get_tool_dependencies("tool_b") == ["tool_a"]
    assert agent_context.get_tool_dependencies("tool_a") == []

def test_context_serialization(agent_context):
    """Test context serialization and deserialization."""
    # Add some state and history
    agent_context.set_state("test_state", {"value": 123})
    agent_context.add_to_history({
        "role": "user",
        "content": "test message",
        "timestamp": datetime.now()
    })
    
    # Serialize context
    serialized = agent_context.serialize()
    
    # Create new context from serialized data
    new_context = AgentContext.deserialize(serialized)
    
    # Verify serialization/deserialization
    assert new_context.get_state("test_state") == {"value": 123}
    assert len(new_context.conversation_history) == 1
    assert new_context.conversation_history[0]["content"] == "test message" 