from setuptools import setup, find_packages

setup(
    name="mcp_finance_agent",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "redis",
        "aiohttp",
        "pydantic",
        "PyYAML"
    ]
) 