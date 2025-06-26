"""
Market data scraper for macroeconomic indicators and market indexes.
"""
import warnings
import yfinance as yf
from fredapi import Fred
import pandas as pd
from functools import reduce
from typing import Dict, Any

from constants import FRED_SERIES, MARKET_INDEXES, MARKET_DATA_FILENAME
from scrapers.base_scraper import BaseScraper
from core.data_processor import DataProcessor

# Suppress FutureWarning from fredapi
warnings.filterwarnings("ignore", category=FutureWarning)


class MarketScraper(BaseScraper):
    """Scraper for market-wide data including indexes and economic indicators."""
    
    def __init__(self, fred_api_key: str):
        """Initialize market scraper.
        
        Args:
            fred_api_key: API key for FRED (Federal Reserve Economic Data)
        """
        self.fred = Fred(api_key=fred_api_key)
        super().__init__("market")
    
    def _fetch_market_indexes(self, start_date: str) -> pd.DataFrame:
        """Fetch market index data from Yahoo Finance.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            
        Returns:
            DataFrame with market index data
        """
        self.logger.info(f"Fetching market indexes from {start_date}")
        frames = []
        
        for name, symbol in MARKET_INDEXES.items():
            try:
                df = yf.download(symbol, start=start_date, auto_adjust=True, progress=False)
                if df.empty:
                    self.logger.warning(f"No data found for {symbol} ({name})")
                    continue
                
                # Process to weekly frequency
                weekly_df = self.data_processor.resample_to_weekly(df, 'Close')
                weekly_df = weekly_df.rename(columns={'Weekly_Close': f"{name}_Weekly_Close"})
                
                frames.append(weekly_df)
                self.logger.info(f"Successfully fetched data for {symbol} ({name})")
                
            except Exception as e:
                self.logger.warning(f"Failed to fetch {symbol} ({name}): {e}")
        
        if not frames:
            return pd.DataFrame(columns=['Date'])
        
        # Merge all index dataframes
        return reduce(
            lambda left, right: pd.merge(left, right, on='Date', how='outer'), 
            frames
        ).sort_values('Date')
    
    def _fetch_fred_data(self, start_date: str) -> pd.DataFrame:
        """Fetch macroeconomic data from FRED.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            
        Returns:
            DataFrame with FRED economic data
        """
        self.logger.info(f"Fetching FRED data from {start_date}")
        fred_data = {}
        
        for name, series_id in FRED_SERIES.items():
            try:
                data = self.fred.get_series(series_id, start_date)
                fred_data[name] = data
                self.logger.debug(f"Successfully fetched {name} from FRED")
            except Exception as e:
                self.logger.warning(f"Error fetching {name} from FRED: {e}")
        
        if not fred_data:
            return pd.DataFrame({'Date': pd.Series(dtype='datetime64[ns]')})
        
        df = pd.DataFrame(fred_data)
        
        # Process FRED data to weekly frequency
        if not df.empty and isinstance(df.index, pd.DatetimeIndex):
            df.index.name = 'Date'
            df = df.resample('W-FRI').last().ffill().reset_index()
        else:
            df = pd.DataFrame({'Date': pd.Series(dtype='datetime64[ns]')})
        
        return df
    
    def _fetch_raw_data(self, start_date: str) -> pd.DataFrame:
        """Fetch and merge all market data.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            
        Returns:
            DataFrame with all market data merged
        """
        # Fetch both types of data
        market_indexes = self._fetch_market_indexes(start_date)
        fred_data = self._fetch_fred_data(start_date)
        
        # Merge the data
        if market_indexes.empty and fred_data.empty:
            return pd.DataFrame()
        
        merged_data = self.data_processor.merge_dataframes(market_indexes, fred_data)
        return merged_data
    
    def _process_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process raw market data.
        
        Args:
            df: Raw market data DataFrame
            
        Returns:
            Processed DataFrame
        """
        if df.empty:
            return df
        
        # Clean column names and normalize dates
        cleaned_df = self.data_processor.clean_market_data_columns(df)
        normalized_df = self.data_processor.normalize_dates(cleaned_df)
        
        return normalized_df
    
    def _get_folder_prefix(self) -> str:
        """Get folder prefix for market data."""
        return "market_data_"
    
    def _get_filename(self) -> str:
        """Get filename for market data."""
        return MARKET_DATA_FILENAME
    
    def fetch_market_data(self, start_date: str) -> pd.DataFrame:
        """Public method to fetch and process market data.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            
        Returns:
            Processed DataFrame with market data
        """
        raw_data = self._fetch_raw_data(start_date)
        if raw_data.empty:
            raise ValueError("No market data found")
        
        return self._process_data(raw_data)
    
    def update_data(self) -> bool:
        """Update existing market data.
        
        Returns:
            True if successful or not needed, False if failed
        """
        return self._update_existing_data()
    
    def save_market_data(self, start_date: str, force: bool = False) -> bool:
        """Save market data.
        
        Args:
            start_date: Start date for data fetching
            force: If True, skip user interaction and overwrite
            
        Returns:
            True if successful, False otherwise
        """
        return self.save_data(start_date, force)
