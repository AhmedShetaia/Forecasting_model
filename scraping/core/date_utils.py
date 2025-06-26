"""
Date utilities for handling trading days and market data availability.
"""
from datetime import datetime, timedelta
from typing import Tuple


def get_last_trading_friday() -> str:
    """Get the last Friday that would have trading data available.
    
    Returns:
        Date string in YYYY-MM-DD format of the last trading Friday
    """
    today = datetime.now()
    
    # If today is Saturday (5) or Sunday (6), go back to Friday
    # If today is Monday-Friday, check if it's before market close
    if today.weekday() == 5:  # Saturday
        last_friday = today - timedelta(days=1)
    elif today.weekday() == 6:  # Sunday  
        last_friday = today - timedelta(days=2)
    else:  # Monday-Friday
        # For simplicity, always use the previous Friday to ensure data availability
        days_back = today.weekday() + 3  # Go back to previous Friday
        last_friday = today - timedelta(days=days_back)
    
    return last_friday.strftime("%Y-%m-%d")


def get_safe_date_range(start_date: str) -> Tuple[str, str]:
    """Get a safe date range for data scraping.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        
    Returns:
        Tuple of (start_date, safe_end_date)
    """
    safe_end_date = get_last_trading_friday()
    return start_date, safe_end_date


def format_date_for_folder(date_str: str) -> str:
    """Convert YYYY-MM-DD to YYYYMMDD format for folder names.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        
    Returns:
        Date in YYYYMMDD format
    """
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return date_obj.strftime("%Y%m%d")
