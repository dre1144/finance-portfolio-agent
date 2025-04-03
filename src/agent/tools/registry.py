"""
Tool registry for MCP agent.
"""

from typing import Dict, Type

from src.agent.tools.base import BaseTool
from src.agent.tools.portfolio import (
    PortfolioInfoTool,
    PortfolioPerformanceTool,
    PortfolioPnLTool,
    PortfolioCashFlowTool,
)


class ToolRegistry:
    """Registry for MCP agent tools."""

    def __init__(self):
        """Initialize tool registry."""
        self._tools: Dict[str, Type[BaseTool]] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """Register default tools."""
        self.register_tool("portfolio_info", PortfolioInfoTool)
        self.register_tool("portfolio_performance", PortfolioPerformanceTool)
        self.register_tool("portfolio_pnl", PortfolioPnLTool)
        self.register_tool("portfolio_cash_flow", PortfolioCashFlowTool)

    def register_tool(self, name: str, tool_class: Type[BaseTool]):
        """Register a tool.
        
        Args:
            name: Tool name
            tool_class: Tool class
        """
        self._tools[name] = tool_class

    def get_tool(self, name: str) -> Type[BaseTool]:
        """Get a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool class
            
        Raises:
            KeyError: If tool not found
        """
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")
        return self._tools[name]

    def list_tools(self) -> Dict[str, Type[BaseTool]]:
        """List all registered tools.
        
        Returns:
            Dictionary of tool names and classes
        """
        return self._tools.copy() 