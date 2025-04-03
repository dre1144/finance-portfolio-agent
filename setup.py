from setuptools import setup, find_packages

setup(
    name="mcp-finance-agent",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "numpy>=1.21.0",
        "pandas>=2.0.3",
        "python-dotenv==1.0.0",
        "tinkoff-invest>=0.2.15",
        "pydantic<2.0.0,>=1.9.2",
        "cryptography>=42.0.5",
        "aiohttp>=3.9.3",
    ],
    extras_require={
        "test": [
            "pytest>=8.0.0",
            "pytest-asyncio>=0.23.5",
            "pytest-cov>=4.1.0",
        ],
    },
) 