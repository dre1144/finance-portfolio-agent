"""
Message analyzer for MCP agent.
"""

import logging
import re
from typing import List

from src.models.base import Message

logger = logging.getLogger(__name__)


class MessageAnalyzer:
    """Analyzer for determining required tools from messages."""

    def __init__(self):
        """Initialize message analyzer."""
        self._patterns = {
            "portfolio_info": [
                r"портфел[ья]",
                r"позици[ия]",
                r"баланс",
                r"состав",
                r"активы",
                r"счет[а]?",
            ],
            "portfolio_performance": [
                r"доходност[ьи]",
                r"результат[ыов]?",
                r"эффективност[ьи]",
                r"прибыльност[ьи]",
                r"показател[ьи]",
                r"метрик[иа]",
            ],
            "portfolio_pnl": [
                r"прибыл[ьи]",
                r"убыт[окка]",
                r"p&?l",
                r"pnl",
                r"доход[ыа]?",
                r"расход[ыа]?",
            ],
            "portfolio_cash_flow": [
                r"поток[иа]?",
                r"движени[еяй]",
                r"ввод[ыа]?",
                r"вывод[ыа]?",
                r"пополнени[еяй]",
                r"списани[еяй]",
            ],
        }
        logger.info("Initialized MessageAnalyzer")

    def analyze_message(self, message: Message) -> List[str]:
        """Analyze message to determine required tools.
        
        Args:
            message: Message to analyze
            
        Returns:
            List of tool names that should be used
        """
        logger.info("Analyzing message: %s", message.content)
        
        # Convert message to lowercase for case-insensitive matching
        content = message.content.lower()
        
        # Find matching tools
        tools = []
        for tool_name, patterns in self._patterns.items():
            for pattern in patterns:
                if re.search(pattern, content):
                    tools.append(tool_name)
                    break
        
        if not tools:
            # Default to portfolio info if no specific tools matched
            tools = ["portfolio_info"]
        
        logger.info("Required tools: %s", tools)
        return tools 