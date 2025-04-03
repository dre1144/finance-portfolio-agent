import pytest
from unittest.mock import MagicMock, patch
from src.agent.message_handler import MessageHandler
from src.models.base import Message, Tool, ToolType


@pytest.fixture
def message_handler(context_manager, tool_registry):
    """Create MessageHandler instance with mocked dependencies."""
    return MessageHandler(context_manager, tool_registry)


@pytest.fixture
def tool_registry():
    """Create ToolRegistry mock."""
    return MagicMock()


async def test_process_message_basic(message_handler, sample_message, context_manager):
    """Test basic message processing without tools."""
    response = await message_handler.process_message(sample_message)
    
    assert isinstance(response, Message)
    assert response.role == "assistant"
    assert len(context_manager.context.messages) == 2  # Original + response


async def test_process_message_with_tool(message_handler, sample_message, sample_tool):
    """Test message processing with a tool."""
    # Mock tool analysis to return our sample tool
    with patch.object(message_handler, '_analyze_message', return_value=[sample_tool]):
        response = await message_handler.process_message(sample_message)
    
    assert isinstance(response, Message)
    assert "tools_used" in response.metadata
    assert sample_tool.name in response.metadata["tools_used"]


async def test_execute_tools_error_handling(message_handler, sample_message, sample_tool):
    """Test error handling during tool execution."""
    # Mock tool execution to raise an exception
    with patch.object(message_handler, '_execute_single_tool', side_effect=Exception("Test error")):
        response = await message_handler._execute_tools(sample_message, [sample_tool])
    
    assert isinstance(response, Message)
    assert "error" in response.metadata["results"][0]
    assert "Test error" in response.metadata["results"][0]["error"]


def test_analyze_message(message_handler, sample_message):
    """Test message analysis functionality."""
    tools = message_handler._analyze_message(sample_message)
    
    assert isinstance(tools, list)
    # Currently returns empty list as per implementation
    assert len(tools) == 0


async def test_execute_single_tool(message_handler, sample_message, sample_tool):
    """Test execution of a single tool."""
    result = await message_handler._execute_single_tool(sample_tool, sample_message)
    
    assert isinstance(result, dict)
    assert result["tool"] == sample_tool.name
    assert result["status"] == "not_implemented"


def test_generate_response(message_handler):
    """Test response generation from tool results."""
    results = [
        {"tool": "test_tool", "status": "success", "data": "test"},
        {"tool": "another_tool", "error": "Test error"}
    ]
    
    response = message_handler._generate_response(results)
    assert isinstance(response, str)
    assert len(response) > 0 