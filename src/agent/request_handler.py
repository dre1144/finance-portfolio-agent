"""
Request handler for MCP agent.
Provides a high-level interface for handling user requests.
"""

from datetime import datetime
from typing import Dict, Any, Optional

from src.models.base import Message, Context
from .message_handler import MessageHandler


class RequestHandler:
    """Handler for user requests."""

    def __init__(self, message_handler: MessageHandler):
        """Initialize request handler.
        
        Args:
            message_handler: Message handler instance
        """
        self.message_handler = message_handler

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a request from the user.
        
        Args:
            request: Request dictionary with type, content, and optional parameters
            
        Returns:
            Response dictionary
        """
        # Convert request to message
        message = Message(
            content=request["content"],
            role="user",
            metadata={
                "type": request["type"],
                "parameters": request.get("parameters", {}),
                "timestamp": request.get("timestamp", datetime.now())
            }
        )
        
        # Create context if needed
        context = request.get("context")
        if context is not None:
            context = Context(**context)
        
        try:
            # Handle message
            response = await self.message_handler.handle_message(message, context)
            
            # Convert response to dictionary
            return {
                "type": request["type"],
                "content": response.message.content,
                "timestamp": datetime.now(),
                "metadata": response.message.metadata,
                "context": response.context.dict() if response.context else None
            }
            
        except Exception as e:
            return {
                "type": "error",
                "content": f"Error processing request: {str(e)}",
                "timestamp": datetime.now(),
                "metadata": {"error": str(e)},
                "context": None
            } 