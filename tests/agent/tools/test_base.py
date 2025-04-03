import pytest
from src.models.base import Tool, ToolType, Message
from src.agent.tools.base import BaseTool


class DummyTool(BaseTool):
    """Dummy tool implementation for testing."""
    
    async def execute(self, message, context):
        """Dummy execution that returns test data."""
        return {"test": "data"}


def test_tool_initialization():
    """Test tool initialization with valid config."""
    config = Tool(
        name="test_tool",
        type=ToolType.ANALYSIS,
        description="Test tool",
        parameters={},
        required_parameters=[]
    )
    
    tool = DummyTool(config)
    assert tool.config == config


def test_tool_validation_name():
    """Test tool validation for missing name."""
    config = Tool(
        name="",
        type=ToolType.ANALYSIS,
        description="Test tool",
        parameters={},
        required_parameters=[]
    )
    
    with pytest.raises(ValueError, match="Tool name is required"):
        DummyTool(config)


def test_tool_validation_type():
    """Test tool validation for missing type."""
    config = Tool(
        name="test_tool",
        type=None,
        description="Test tool",
        parameters={},
        required_parameters=[]
    )
    
    with pytest.raises(ValueError, match="Tool type is required"):
        DummyTool(config)


def test_tool_validation_parameters():
    """Test tool validation for missing required parameters."""
    config = Tool(
        name="test_tool",
        type=ToolType.ANALYSIS,
        description="Test tool",
        parameters={},
        required_parameters=["param1"]
    )
    
    with pytest.raises(ValueError, match="Missing required parameters: param1"):
        DummyTool(config)


def test_get_parameter():
    """Test getting parameter values."""
    config = Tool(
        name="test_tool",
        type=ToolType.ANALYSIS,
        description="Test tool",
        parameters={"param1": "value1"},
        required_parameters=[]
    )
    
    tool = DummyTool(config)
    assert tool.get_parameter("param1") == "value1"
    assert tool.get_parameter("param2", "default") == "default"


def test_extract_parameters():
    """Test parameter extraction from message."""
    config = Tool(
        name="test_tool",
        type=ToolType.ANALYSIS,
        description="Test tool",
        parameters={},
        required_parameters=[]
    )
    
    tool = DummyTool(config)
    message = Message(content="test message", role="user")
    params = tool.extract_parameters(message)
    assert isinstance(params, dict)
    assert len(params) == 0  # Default implementation returns empty dict 