import pytest
from src.agent.tools.registry import ToolRegistry
from src.models.base import ToolType


def test_registry_initialization():
    """Test that registry is properly initialized."""
    registry = ToolRegistry()
    assert len(registry._tools) == 0
    assert all(len(tools) == 0 for tools in registry._tool_types.values())


def test_register_tool(sample_tool):
    """Test registering a new tool."""
    registry = ToolRegistry()
    registry.register_tool(sample_tool)
    
    assert len(registry._tools) == 1
    assert registry._tools[sample_tool.name] == sample_tool
    assert len(registry._tool_types[sample_tool.type]) == 1


def test_register_duplicate_tool(sample_tool):
    """Test that registering duplicate tool raises error."""
    registry = ToolRegistry()
    registry.register_tool(sample_tool)
    
    with pytest.raises(ValueError):
        registry.register_tool(sample_tool)


def test_get_tool(sample_tool):
    """Test retrieving tool by name."""
    registry = ToolRegistry()
    registry.register_tool(sample_tool)
    
    tool = registry.get_tool(sample_tool.name)
    assert tool == sample_tool
    
    tool = registry.get_tool("non_existent")
    assert tool is None


def test_get_tools_by_type(sample_tool):
    """Test retrieving tools by type."""
    registry = ToolRegistry()
    registry.register_tool(sample_tool)
    
    tools = registry.get_tools_by_type(sample_tool.type)
    assert len(tools) == 1
    assert tools[0] == sample_tool
    
    tools = registry.get_tools_by_type(ToolType.PORTFOLIO)
    assert len(tools) == 0


def test_list_tools(sample_tool):
    """Test listing all registered tools."""
    registry = ToolRegistry()
    registry.register_tool(sample_tool)
    
    tools = registry.list_tools()
    assert len(tools) == 1
    assert tools[0] == sample_tool


def test_unregister_tool(sample_tool):
    """Test unregistering a tool."""
    registry = ToolRegistry()
    registry.register_tool(sample_tool)
    
    registry.unregister_tool(sample_tool.name)
    assert len(registry._tools) == 0
    assert len(registry._tool_types[sample_tool.type]) == 0
    
    # Test unregistering non-existent tool
    registry.unregister_tool("non_existent")  # Should not raise error 