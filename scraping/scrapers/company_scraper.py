"""
Company-specific stock data scraper.
"""
import yfinance as yf
import pandas as pd
from typing import Optional

from ..constants import COMPANY_DATA_FILENAME, WEEKLY_CLOSE_COLUMN
from .base_scraper import BaseScraper
from ..core.data_processor import DataProcessor


class CompanyScraper(BaseScraper):
    """Scraper for individual company stock data."""
    
    def __init__(self, ticker: str):
        """Initialize company scraper.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
        """
        self.ticker = ticker.upper()
        super().__init__(self.ticker)
    
    def _fetch_raw_data(self, start_date: str, end_date: str = None) -> pd.DataFrame:
        """Fetch stock price data from Yahoo Finance.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (optional)
            
        Returns:
            DataFrame with stock price data
        """
        # Import here to avoid circular imports
        from core.date_utils import get_last_trading_friday
        
        # Use safe end date if not provided
        if end_date is None:
            end_date = get_last_trading_friday()
            
        self.logger.info(f"Fetching stock data for {self.ticker} from {start_date} to {end_date}")
        
        try:
            stock = yf.Ticker(self.ticker)
            df = stock.history(start=start_date, end=end_date, auto_adjust=True, actions=False)
            
            if df.empty:
                self.logger.warning(f"No data found for ticker {self.ticker} from {start_date}")
                return pd.DataFrame()
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching data for {self.ticker}: {e}")
            return pd.DataFrame()
    
    def _process_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process raw stock data to weekly frequency.
        
        Args:
            df: Raw daily stock data
            
        Returns:
            Processed weekly DataFrame
        """
        if df.empty:
            return df
        
        # Resample to weekly frequency and rename column
        weekly_df = self.data_processor.resample_to_weekly(df, 'Close')
        weekly_df = weekly_df.rename(columns={WEEKLY_CLOSE_COLUMN: 'Weekly_Close'})
        
        return weekly_df
    
    def _get_folder_prefix(self) -> str:
        """Get folder prefix for company data."""
        return f"{self.ticker}_"
    
    def _get_filename(self) -> str:
        """Get filename for company data."""
        return COMPANY_DATA_FILENAME.format(ticker=self.ticker)
    
    def fetch_stock_data(self, start_date: str, end_date: str = None) -> pd.DataFrame:
        """Public method to fetch and process stock data.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (optional)
            
        Returns:
            Processed DataFrame with weekly stock data
        """
        raw_data = self._fetch_raw_data(start_date, end_date)
        if raw_data.empty:
            raise ValueError(f"No data found for ticker {self.ticker}")
        
        return self._process_data(raw_data)
    
    def update_data(self) -> bool:
        """Update existing company data.
        
        Returns:
            True if successful or not needed, False if failed
        """
        return self._update_existing_data()
    
    def save_company_data(self, start_date: str, force: bool = False) -> bool:
        """Save company stock data.
        
        Args:
            start_date: Start date for data fetching
            force: If True, skip user interaction and overwrite
            
        Returns:
            True if successful, False otherwise
        """
        return self.save_data(start_date, force)
