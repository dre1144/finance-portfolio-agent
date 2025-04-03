import pytest
from src.models.base import Message


async def test_portfolio_request_flow(
    message_handler,
    tool_registry,
    portfolio_tool,
    redis_mock
):
    """Test complete flow for portfolio request."""
    # Register tool
    tool_registry.register_tool(portfolio_tool)
    
    # Create test message
    message = Message(
        content="Покажи мой портфель",
        role="user"
    )
    
    # Process message
    response = await message_handler.process_message(message)
    
    # Verify response
    assert response.role == "assistant"
    assert "total_value: 100000.0" in response.content
    assert "currency: RUB" in response.content
    
    # Verify context was updated
    assert len(message_handler.context_manager.context.messages) == 2
    assert message_handler.context_manager.context.messages[0] == message
    assert message_handler.context_manager.context.messages[1] == response
    
    # Verify Redis interactions
    assert redis_mock.set.call_count == 2  # Two messages saved


async def test_analysis_request_flow(
    message_handler,
    tool_registry,
    analysis_tool,
    redis_mock
):
    """Test complete flow for analysis request."""
    # Register tool
    tool_registry.register_tool(analysis_tool)
    
    # Create test message
    message = Message(
        content="Проведи анализ рисков",
        role="user"
    )
    
    # Process message
    response = await message_handler.process_message(message)
    
    # Verify response
    assert response.role == "assistant"
    assert "risk_level: moderate" in response.content
    assert "volatility: 0.15" in response.content
    assert "sharpe_ratio: 1.2" in response.content
    
    # Verify context was updated
    assert len(message_handler.context_manager.context.messages) == 2
    
    # Verify Redis interactions
    assert redis_mock.set.call_count == 2


async def test_multiple_tools_flow(
    message_handler,
    tool_registry,
    portfolio_tool,
    analysis_tool,
    redis_mock
):
    """Test flow with multiple tools."""
    # Register tools
    tool_registry.register_tool(portfolio_tool)
    tool_registry.register_tool(analysis_tool)
    
    # Create test message
    message = Message(
        content="Покажи портфель и проведи анализ рисков",
        role="user"
    )
    
    # Process message
    response = await message_handler.process_message(message)
    
    # Verify response includes both tool results
    assert "total_value: 100000.0" in response.content
    assert "risk_level: moderate" in response.content
    
    # Verify tools used
    assert len(response.metadata["tools_used"]) == 2
    assert "portfolio" in response.metadata["tools_used"]
    assert "analysis" in response.metadata["tools_used"]
    
    # Verify all results successful
    assert all(r["status"] == "success" for r in response.metadata["results"])


async def test_conversation_context_flow(
    message_handler,
    tool_registry,
    portfolio_tool,
    redis_mock
):
    """Test conversation context preservation."""
    # Register tool
    tool_registry.register_tool(portfolio_tool)
    
    # First message
    message1 = Message(
        content="Покажи мой портфель",
        role="user"
    )
    response1 = await message_handler.process_message(message1)
    
    # Second message referencing first
    message2 = Message(
        content="А какая общая стоимость?",
        role="user"
    )
    response2 = await message_handler.process_message(message2)
    
    # Verify conversation history
    history = message_handler.context_manager.get_conversation_history()
    assert len(history) == 4  # 2 messages + 2 responses
    assert history[0] == message1
    assert history[1] == response1
    assert history[2] == message2
    assert history[3] == response2


async def test_error_handling_flow(
    message_handler,
    tool_registry,
    redis_mock
):
    """Test error handling in the flow."""
    # Create test message without any registered tools
    message = Message(
        content="Покажи портфель",
        role="user"
    )
    
    # Process message
    response = await message_handler.process_message(message)
    
    # Verify error response
    assert response.role == "assistant"
    assert "не смог определить" in response.content
    assert len(response.metadata["tools_used"]) == 0
    
    # Verify context still updated
    assert len(message_handler.context_manager.context.messages) == 2
    assert redis_mock.set.call_count == 2 