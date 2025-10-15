from langchain_core.tools import tool
import requests


@tool
def get_stock_price(symbol : str) -> dict:
    """
    Get latest stock price for a given symbol (e.g 'AAPL', 'TSLA')
    using Aplha Vantage with API key in the URL.
    """

    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=YOURAPIKEY"

    response = requests.get(url)

    return response.json()