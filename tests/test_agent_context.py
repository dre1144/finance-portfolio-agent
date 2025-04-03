import pytest
import json
from unittest.mock import MagicMock
from src.models.base import Message, Tool, ToolType
from src.agent.context import AgentContext


def test_context_initialization(agent_context):
    """Test that context is properly initialized."""
    assert agent_context.context is not None
    assert agent_context.context.messages == []
    assert agent_context.context.tools == []
    assert agent_context.context.metadata == {}


def test_add_message(agent_context, sample_message):
    """Test adding message to context."""
    agent_context.add_message(sample_message)
    
    messages = agent_context.get_conversation_history()
    assert len(messages) == 1
    assert messages[0].content == sample_message.content
    assert messages[0].role == sample_message.role


def test_add_tool(agent_context, sample_tool):
    """Test adding tool to context."""
    agent_context.add_tool(sample_tool)
    
    tool = agent_context.get_tool_by_name(sample_tool.name)
    assert tool is not None
    assert tool.name == sample_tool.name
    assert tool.type == sample_tool.type
    assert tool.description == sample_tool.description


def test_get_conversation_history_with_limit(agent_context):
    """Test getting limited conversation history."""
    # Add multiple messages
    messages = [
        Message(content=f"Message {i}", role="user")
        for i in range(5)
    ]
    for msg in messages:
        agent_context.add_message(msg)
    
    # Get limited history
    history = agent_context.get_conversation_history(limit=3)
    assert len(history) == 3
    assert [msg.content for msg in history] == ["Message 2", "Message 3", "Message 4"]


def test_update_metadata(agent_context):
    """Test updating context metadata."""
    agent_context.update_metadata("test_key", "test_value")
    assert agent_context.context.metadata["test_key"] == "test_value"


def test_clear_context(agent_context, sample_message, sample_tool):
    """Test clearing context."""
    # Add data to context
    agent_context.add_message(sample_message)
    agent_context.add_tool(sample_tool)
    agent_context.update_metadata("test_key", "test_value")
    
    # Clear context
    agent_context.clear_context()
    
    # Verify context is empty
    assert len(agent_context.get_conversation_history()) == 0
    assert agent_context.get_tool_by_name(sample_tool.name) is None
    assert agent_context.context.metadata == {}


def test_context_persistence(redis_mock, agent_context, sample_message):
    """Test that context is saved to Redis."""
    agent_context.add_message(sample_message)
    
    # Verify Redis set was called
    redis_mock.set.assert_called_with("mcp:context", agent_context.context.json())


def test_load_context(redis_mock, agent_context):
    """Test loading context from Redis."""
    # Setup mock Redis response
    mock_context = {
        "messages": [
            {"content": "Test message", "role": "user"}
        ],
        "tools": [],
        "metadata": {"test_key": "test_value"}
    }
    redis_mock.get.return_value = json.dumps(mock_context)
    
    # Load context
    agent_context.load_context()
    
    # Verify context was loaded
    assert len(agent_context.get_conversation_history()) == 1
    assert agent_context.context.metadata["test_key"] == "test_value"


def test_get_nonexistent_tool(agent_context):
    """Test getting tool that doesn't exist."""
    tool = agent_context.get_tool_by_name("nonexistent")
    assert tool is None 