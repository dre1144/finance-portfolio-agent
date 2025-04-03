import pytest
from src.agent.message_analyzer import MessageAnalyzer
from src.models.base import Message, Tool, ToolType


@pytest.fixture
def analyzer():
    """Create MessageAnalyzer instance."""
    return MessageAnalyzer()


@pytest.fixture
def sample_tools():
    """Create sample tools for testing."""
    return [
        Tool(
            name="portfolio_analyzer",
            type=ToolType.PORTFOLIO,
            description="Portfolio analysis tool",
            parameters={},
            required_parameters=[]
        ),
        Tool(
            name="risk_analyzer",
            type=ToolType.ANALYSIS,
            description="Risk analysis tool",
            parameters={},
            required_parameters=[]
        ),
        Tool(
            name="market_data",
            type=ToolType.MARKET,
            description="Market data tool",
            parameters={},
            required_parameters=[]
        )
    ]


def test_identify_portfolio_type(analyzer):
    """Test identifying portfolio-related messages."""
    content = "Покажи мой портфель и его текущий баланс"
    types = analyzer._identify_required_types(content)
    assert ToolType.PORTFOLIO in types

    content = "Какая доходность у моего портфеля?"
    types = analyzer._identify_required_types(content)
    assert ToolType.PORTFOLIO in types


def test_identify_analysis_type(analyzer):
    """Test identifying analysis-related messages."""
    content = "Проведи анализ рисков портфеля"
    types = analyzer._identify_required_types(content)
    assert ToolType.ANALYSIS in types

    content = "Рассчитай волатильность и VaR"
    types = analyzer._identify_required_types(content)
    assert ToolType.ANALYSIS in types


def test_identify_market_type(analyzer):
    """Test identifying market-related messages."""
    content = "Покажи рыночные цены акций"
    types = analyzer._identify_required_types(content)
    assert ToolType.MARKET in types

    content = "Построй график котировок"
    types = analyzer._identify_required_types(content)
    assert ToolType.MARKET in types


def test_identify_recommendation_type(analyzer):
    """Test identifying recommendation-related messages."""
    content = "Дай рекомендации по оптимизации портфеля"
    types = analyzer._identify_required_types(content)
    assert ToolType.RECOMMENDATION in types

    content = "Нужно ребалансировать портфель"
    types = analyzer._identify_required_types(content)
    assert ToolType.RECOMMENDATION in types


def test_identify_multiple_types(analyzer):
    """Test identifying messages requiring multiple tool types."""
    content = "Проанализируй риски портфеля и дай рекомендации"
    types = analyzer._identify_required_types(content)
    assert ToolType.ANALYSIS in types
    assert ToolType.RECOMMENDATION in types


def test_analyze_message(analyzer, sample_tools):
    """Test full message analysis with tool selection."""
    message = Message(
        content="Покажи состав портфеля и проведи анализ рисков",
        role="user"
    )
    
    selected_tools = analyzer.analyze(message, sample_tools)
    assert len(selected_tools) == 2
    assert any(t.type == ToolType.PORTFOLIO for t in selected_tools)
    assert any(t.type == ToolType.ANALYSIS for t in selected_tools)


def test_analyze_no_match(analyzer, sample_tools):
    """Test analysis of message with no matching patterns."""
    message = Message(
        content="Привет, как дела?",
        role="user"
    )
    
    selected_tools = analyzer.analyze(message, sample_tools)
    assert len(selected_tools) == 0


def test_analyze_unavailable_tool_type(analyzer, sample_tools):
    """Test handling of matched type with no available tools."""
    message = Message(
        content="Дай рекомендации по портфелю",
        role="user"
    )
    
    # No recommendation tools in sample_tools
    selected_tools = analyzer.analyze(message, sample_tools)
    assert not any(t.type == ToolType.RECOMMENDATION for t in selected_tools) 