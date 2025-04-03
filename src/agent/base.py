"""
Base classes for MCP agent.
"""

from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv
from ..services.tinkoff.client import TinkoffClient
from ..services.tinkoff.portfolio import PortfolioService
from ..utils.security import TokenSecurity
from abc import ABC, abstractmethod
from src.models.base import Message, Tool

class TinkoffAgent:
    def __init__(self):
        load_dotenv()
        self.security = TokenSecurity()
        self._setup_client()

    def _setup_client(self):
        token = os.getenv('TINKOFF_TOKEN')
        if not token:
            raise ValueError("Token not found in environment variables")
        
        self.client = TinkoffClient(token)
        self.portfolio_service = PortfolioService(self.client)

    def __enter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.close()

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass  # Sync context manager is a no-op, use async context manager instead

    @property
    def is_sandbox(self) -> bool:
        return self.environment == 'SANDBOX'

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