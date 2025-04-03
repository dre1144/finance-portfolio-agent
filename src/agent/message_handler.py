"""
Message handler for MCP agent.
"""

import logging
from typing import Dict, Any, List, Optional

from src.models.base import Message, Context, AgentResponse
from src.services.tinkoff.portfolio import PortfolioService
from .message_analyzer import MessageAnalyzer
from .tools.executor import ToolExecutor

logger = logging.getLogger(__name__)


class MessageHandler:
    """Handler for MCP agent messages."""

    def __init__(self, portfolio_service: PortfolioService):
        """Initialize message handler.
        
        Args:
            portfolio_service: Portfolio service instance
        """
        self.portfolio_service = portfolio_service
        self.analyzer = MessageAnalyzer()
        self.executor = ToolExecutor(portfolio_service)
        logger.info("Initialized MessageHandler")

    async def handle_message(
        self,
        message: Message,
        context: Optional[Context] = None,
    ) -> AgentResponse:
        """Handle a message from the user.
        
        Args:
            message: Message from the user
            context: Optional conversation context
            
        Returns:
            Agent response
        """
        logger.info("Handling message: %s", message.content)
        
        # Create new context if not provided
        if context is None:
            context = Context()
        
        # Add message to context
        context.messages.append(message)
        
        try:
            # Analyze message to determine required tools
            tool_names = self.analyzer.analyze_message(message)
            logger.info("Required tools: %s", tool_names)
            
            # Execute tools
            tool_results = []
            for tool_name in tool_names:
                try:
                    result = await self.executor.execute(
                        tool_name=tool_name,
                        message=message,
                        context={"context": context},
                    )
                    tool_results.append({
                        "tool": tool_name,
                        "status": "success",
                        "result": result,
                    })
                except Exception as e:
                    logger.error("Tool execution failed: %s - %s", tool_name, str(e))
                    tool_results.append({
                        "tool": tool_name,
                        "status": "error",
                        "error": str(e),
                    })
            
            # Generate response message
            response_message = Message(
                content=self._generate_response(message, tool_results),
                role="assistant",
                metadata={"tool_results": tool_results},
            )
            
            # Add response to context
            context.messages.append(response_message)
            
            return AgentResponse(
                message=response_message,
                context=context,
                tool_calls=tool_results,
            )
            
        except Exception as e:
            logger.error("Message handling failed: %s", str(e))
            error_message = Message(
                content=f"Error processing message: {str(e)}",
                role="assistant",
                metadata={"error": str(e)},
            )
            context.messages.append(error_message)
            return AgentResponse(
                message=error_message,
                context=context,
            )

    def _generate_response(
        self,
        message: Message,
        tool_results: List[Dict[str, Any]],
    ) -> str:
        """Generate response message based on tool results.
        
        Args:
            message: Original message
            tool_results: Results from tool executions
            
        Returns:
            Response message content
        """
        # Check if any tools failed
        failed_tools = [
            result["tool"]
            for result in tool_results
            if result["status"] == "error"
        ]
        
        if failed_tools:
            return (
                f"Sorry, I encountered errors while processing your request. "
                f"The following tools failed: {', '.join(failed_tools)}"
            )
        
        # Combine successful tool results
        response_parts = []
        for result in tool_results:
            if result["status"] == "success":
                response_parts.append(self._format_tool_result(result))
        
        return "\n\n".join(response_parts)

    def _format_tool_result(self, result: Dict[str, Any]) -> str:
        """Format tool result for response message.
        
        Args:
            result: Tool execution result
            
        Returns:
            Formatted result string
        """
        tool_name = result["tool"]
        tool_result = result["result"]
        
        if tool_name == "portfolio_info":
            return self._format_portfolio_info(tool_result)
        elif tool_name == "portfolio_performance":
            return self._format_portfolio_performance(tool_result)
        elif tool_name == "portfolio_pnl":
            return self._format_portfolio_pnl(tool_result)
        elif tool_name == "portfolio_cash_flow":
            return self._format_portfolio_cash_flow(tool_result)
        else:
            return str(tool_result)

    def _format_portfolio_info(self, result: Dict[str, Any]) -> str:
        """Format portfolio info result.
        
        Args:
            result: Portfolio info result
            
        Returns:
            Formatted string
        """
        return (
            f"Portfolio Information\n"
            f"Account: {result['account_id']}\n"
            f"Total Value: {result['total_value']}\n"
            f"Positions: {len(result['positions'])}\n"
            f"Last Updated: {result['last_update']}"
        )

    def _format_portfolio_performance(self, result: Dict[str, Any]) -> str:
        """Format portfolio performance result.
        
        Args:
            result: Portfolio performance result
            
        Returns:
            Formatted string
        """
        metrics = result["metrics"]
        base_info = (
            f"Portfolio Performance ({result['period']})\n"
            f"Account: {result['account_id']}\n"
            f"Currency: {result['currency']}\n"
            f"Absolute Return: {metrics['absolute_return']['value']} {metrics['absolute_return']['currency']}\n"
            f"Relative Return: {metrics['relative_return']}%\n"
            f"Annualized Return: {metrics['annualized_return']}%"
        )
        
        if "volatility" in metrics:
            base_info += f"\nVolatility: {metrics['volatility']}%"
            
        return base_info

    def _format_portfolio_pnl(self, result: Dict[str, Any]) -> str:
        """Format portfolio PnL result.
        
        Args:
            result: Portfolio PnL result
            
        Returns:
            Formatted string
        """
        return (
            f"Portfolio Profit & Loss ({result['period']})\n"
            f"Account: {result['account_id']}\n"
            f"Currency: {result['currency']}\n"
            f"Realized PnL: {result['realized_pnl']}\n"
            f"Unrealized PnL: {result['unrealized_pnl']}\n"
            f"Total PnL: {result['total_pnl']}"
        )

    def _format_portfolio_cash_flow(self, result: Dict[str, Any]) -> str:
        """Format portfolio cash flow result.
        
        Args:
            result: Portfolio cash flow result
            
        Returns:
            Formatted string
        """
        return (
            f"Portfolio Cash Flow ({result['period']})\n"
            f"Account: {result['account_id']}\n"
            f"Currency: {result['currency']}\n"
            f"Inflow: {result['inflow']}\n"
            f"Outflow: {result['outflow']}\n"
            f"Net Flow: {result['net_flow']}"
        ) 