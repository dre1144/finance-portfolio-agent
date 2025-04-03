"""
Tool executor for MCP agent.
"""

import logging
from typing import Dict, Any, Optional

from src.models.base import Message, Tool
from src.services.tinkoff.portfolio import PortfolioService
from .registry import ToolRegistry

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Executor for MCP agent tools."""

    def __init__(self, portfolio_service: PortfolioService):
        """Initialize tool executor.
        
        Args:
            portfolio_service: Portfolio service instance
        """
        self.portfolio_service = portfolio_service
        self.registry = ToolRegistry()
        logger.info("Initialized ToolExecutor")

    async def execute(
        self,
        tool_name: str,
        message: Message,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a tool.
        
        Args:
            tool_name: Name of the tool to execute
            message: Message that triggered the tool
            context: Additional context for execution
            
        Returns:
            Tool execution results
            
        Raises:
            KeyError: If tool not found
            ValueError: If tool execution fails
        """
        logger.info("Executing tool: %s", tool_name)
        
        try:
            # Get tool class from registry
            tool_class = self.registry.get_tool(tool_name)
            
            # Create tool instance with portfolio service
            tool = tool_class(self.portfolio_service)
            
            # Execute tool
            result = await tool.execute(message, context or {})
            logger.info("Tool execution successful: %s", tool_name)
            return result
            
        except KeyError as e:
            logger.error("Tool not found: %s", tool_name)
            raise
            
        except Exception as e:
            logger.error("Tool execution failed: %s - %s", tool_name, str(e))
            raise ValueError(f"Tool execution failed: {str(e)}")

    def list_tools(self) -> Dict[str, str]:
        """List all available tools.
        
        Returns:
            Dictionary of tool names and descriptions
        """
        tools = self.registry.list_tools()
        return {
            name: tool_class(self.portfolio_service).config.description
            for name, tool_class in tools.items()
        } 