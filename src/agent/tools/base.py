"""
Base classes for MCP agent tools.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from src.models.base import Message, Tool


class BaseTool(ABC):
    """Base class for all tools."""

    def __init__(self, tool_config: Tool):
        """Initialize tool with configuration.
        
        Args:
            tool_config: Tool configuration
        """
        self.config = tool_config
        self.validate_config()

    @abstractmethod
    async def execute(self, message: Message, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given message and context.
        
        Args:
            message: Message that triggered the tool
            context: Additional context for execution
            
        Returns:
            Tool execution results
        """
        pass

    def validate_config(self) -> None:
        """Validate tool configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        if not self.config.name:
            raise ValueError("Tool name is required")
        if not self.config.type:
            raise ValueError("Tool type is required")
        
        # Validate required parameters are present
        missing_params = [
            param for param in self.config.required_parameters
            if param not in self.config.parameters
        ]
        if missing_params:
            raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")

    def get_parameter(self, name: str, default: Any = None) -> Any:
        """Get parameter value from configuration.
        
        Args:
            name: Parameter name
            default: Default value if parameter is not found
            
        Returns:
            Parameter value or default
        """
        return self.config.parameters.get(name, default)

    def extract_parameters(self, message: Message) -> Dict[str, Any]:
        """Extract tool parameters from message.
        
        Args:
            message: Message to extract parameters from
            
        Returns:
            Dictionary of extracted parameters
        """
        params = {}
        
        # Extract parameters from message metadata if available
        if message.metadata:
            params = {
                key: value
                for key, value in message.metadata.items()
                if key in self.config.parameters
            }
        
        # Set default values for missing parameters
        for name, param in self.config.parameters.items():
            if name not in params and "default" in param:
                params[name] = param["default"]
        
        return params 