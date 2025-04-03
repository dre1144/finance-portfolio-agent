import requests
import json
from datetime import datetime, timedelta

def test_agent():
    base_url = 'http://localhost:8000'
    
    # Test the health endpoint
    response = requests.get(f'{base_url}/health')
    print(f"Health check response: {response.status_code}")
    print(f"Response content: {response.json()}\n")
    
    # Test getting account info
    response = requests.get(f'{base_url}/account')
    print(f"Account info response: {response.status_code}")
    print(f"Response content: {response.json()}\n")
    
    # Test getting portfolio
    response = requests.get(f'{base_url}/portfolio')
    print(f"Portfolio response: {response.status_code}")
    print(f"Response content: {response.json()}\n")
    
    # Set date range for reports (last 30 days)
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    print(f"Using date range: {from_date} to {to_date}\n")
    
    # Test P&L report
    response = requests.get(
        f'{base_url}/reports/pnl',
        params={'from_date': from_date, 'to_date': to_date}
    )
    print(f"P&L report URL: {response.url}")
    print(f"P&L report response: {response.status_code}")
    print(f"Response content: {response.json()}\n")
    
    # Test Cash Flow report
    response = requests.get(
        f'{base_url}/reports/cash-flow',
        params={'from_date': from_date, 'to_date': to_date}
    )
    print(f"Cash Flow report URL: {response.url}")
    print(f"Cash Flow report response: {response.status_code}")
    print(f"Response content: {response.json()}\n")
    
    # Test Portfolio Performance report
    response = requests.get(
        f'{base_url}/reports/portfolio-performance',
        params={'from_date': from_date, 'to_date': to_date}
    )
    print(f"Portfolio Performance report URL: {response.url}")
    print(f"Portfolio Performance report response: {response.status_code}")
    print(f"Response content: {response.json()}\n")

if __name__ == "__main__":
    test_agent() 