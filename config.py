"""Configuration settings for the MCP agent."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Tinkoff API configuration
TINKOFF_TOKEN = os.getenv("TINKOFF_TOKEN")
if not TINKOFF_TOKEN:
    raise ValueError("TINKOFF_TOKEN environment variable is not set")

# API endpoints
TINKOFF_API_URL = "https://api-invest.tinkoff.ru/openapi"

# Other settings
DEFAULT_CURRENCY = "USD"
DEFAULT_PERIOD = "month" 