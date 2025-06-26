"""
Constants and configuration values for the financial data scraper.
"""
from typing import Dict, List

# Date and time constants
DEFAULT_START_DATE: str = "2020-01-01"
DATE_FORMAT: str = "%Y-%m-%d"
FOLDER_DATE_FORMAT: str = "%Y%m%d"
WEEKLY_FREQUENCY: str = "W-FRI"

# File and directory constants
OUTPUT_DIR: str = "scraping/scraped_data"
COMPANY_DATA_FILENAME: str = "{ticker}_data.csv"
MARKET_DATA_FILENAME: str = "market_data.csv"

# Data processing constants
DAYS_FOR_RECENT_CHECK: int = 7
DEFAULT_RESAMPLE_METHOD: str = "last"

# FRED Series IDs
FRED_SERIES: Dict[str, str] = {
    'CPI': 'CPIAUCSL',
    'UnemploymentRate': 'UNRATE',
    'FEDFUNDS': 'FEDFUNDS',
    'DFF': 'DFF',
    'GDP': 'GDP'
}

# Market indexes
MARKET_INDEXES: Dict[str, str] = {
    'SP500': '^GSPC',
    'NASDAQ': '^IXIC',
    'VIX': '^VIX'
}

# Default tickers for bulk operations
DEFAULT_TICKERS: List[str] = [
    "AAPL", "NFLX", "ADBE", "AMZN", "GOOGL", 
    "MSFT", "TSLA", "META", "NVDA", "PYPL"
]

# User interaction constants
OVERWRITE_CHOICE_MAP: Dict[str, str] = {
    'a': 'overwrite',
    'b': 'update', 
    'c': 'skip'
}

# Column naming constants
WEEKLY_CLOSE_COLUMN: str = "Weekly_Close"
DATE_COLUMN: str = "Date"
