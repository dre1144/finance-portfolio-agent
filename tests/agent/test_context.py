import json
import pytest
from src.models.base import Context, Message


def test_context_initialization(context_manager):
    """Test that context is properly initialized."""
    assert context_manager.context is not None
    assert isinstance(context_manager.context, Context)
    assert len(context_manager.context.messages) == 0
    assert len(context_manager.context.tools) == 0


def test_add_message(context_manager, sample_message, redis_mock):
    """Test adding message to context."""
    context_manager.add_message(sample_message)
    
    assert len(context_manager.context.messages) == 1
    assert context_manager.context.messages[0] == sample_message
    redis_mock.set.assert_called_once()


def test_add_tool(context_manager, sample_tool, redis_mock):
    """Test adding tool to context."""
    context_manager.add_tool(sample_tool)
    
    assert len(context_manager.context.tools) == 1
    assert context_manager.context.tools[0] == sample_tool
    redis_mock.set.assert_called_once()


def test_update_metadata(context_manager, redis_mock):
    """Test updating context metadata."""
    key, value = "test_key", "test_value"
    context_manager.update_metadata(key, value)
    
    assert context_manager.context.metadata[key] == value
    redis_mock.set.assert_called_once()


def test_get_conversation_history(context_manager, sample_message):
    """Test retrieving conversation history."""
    context_manager.add_message(sample_message)
    messages = context_manager.get_conversation_history()
    
    assert len(messages) == 1
    assert messages[0] == sample_message

    # Test with limit
    messages = context_manager.get_conversation_history(limit=1)
    assert len(messages) == 1


def test_get_tool_by_name(context_manager, sample_tool):
    """Test retrieving tool by name."""
    context_manager.add_tool(sample_tool)
    
    tool = context_manager.get_tool_by_name(sample_tool.name)
    assert tool == sample_tool
    
    tool = context_manager.get_tool_by_name("non_existent")
    assert tool is None


def test_load_context(context_manager, redis_mock, sample_message):
    """Test loading context from Redis."""
    context = Context(messages=[sample_message])
    redis_mock.get.return_value = context.model_dump_json()
    
    context_manager.load_context()
    assert len(context_manager.context.messages) == 1
    assert context_manager.context.messages[0] == sample_message


def test_clear_context(context_manager, sample_message, redis_mock):
    """Test clearing context."""
    context_manager.add_message(sample_message)
    context_manager.clear_context()
    
    assert len(context_manager.context.messages) == 0
    redis_mock.delete.assert_called_once_with("mcp:context") 