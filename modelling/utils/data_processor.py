"""Data processing utilities for time series data."""
import os
import pandas as pd
from datetime import datetime
import logging
from pathlib import Path
from ..config.constants import SCRAPED_DATA_DIR, DATE_FORMAT

logger = logging.getLogger(__name__)


class DataProcessor:
    """Class for processing time series data for forecasting models."""
    
    def __init__(self, scraped_folder=None):
        """Initialize data processor.
        
        Args:
            scraped_folder: Path to folder containing scraped data
        """
        self.scraped_folder = scraped_folder or SCRAPED_DATA_DIR
        
    def _extract_dates_from_folder(self, folder_name):
        """Extract start and end dates from folder name.
        
        Args:
            folder_name: Folder name in format TICKER_YYYYMMDD_YYYYMMDD
            
        Returns:
            Tuple of (start_date, end_date) as datetime objects, or (None, None) if parsing fails
        """
        parts = folder_name.split('_')
        if len(parts) >= 3:
            try:
                start_date = datetime.strptime(parts[1], DATE_FORMAT)
                end_date = datetime.strptime(parts[2], DATE_FORMAT)
                return start_date, end_date
            except ValueError:
                logger.warning(f"Failed to parse dates from folder name: {folder_name}")
        
        return None, None
    
    def find_company_folder(self, ticker):
        """Find the folder containing data for a specific company.
        
        Args:
            ticker: Company ticker symbol
            
        Returns:
            Path to the company data folder, or None if not found
        """
        scraped_folder = Path(self.scraped_folder)
        
        # Look for folders with the ticker prefix
        for item in scraped_folder.glob(f"{ticker}_*"):
            if item.is_dir():
                return item
                
        logger.warning(f"No data folder found for ticker {ticker}")
        return None
    
    def load_company_data(self, ticker):
        """Load data for a specific company.
        
        Args:
            ticker: Company ticker symbol
            
        Returns:
            Tuple of (data_df, start_date, end_date)
            
        Raises:
            ValueError: If no valid data is found for the ticker
        """
        data = None
        start_date = None
        end_date = None
        
        # Find the company's folder
        folder_path = self.find_company_folder(ticker)
        
        if folder_path:
            start_date, end_date = self._extract_dates_from_folder(folder_path.name)
            
            # Look for the company's data file
            data_file = f"{ticker}_data.csv"
            file_path = folder_path / data_file
            
            if file_path.exists():
                try:
                    df = pd.read_csv(file_path)
                    
                    # Ensure required columns exist
                    required_cols = ['Date', 'Weekly_Close']
                    if not all(col in df.columns for col in required_cols):
                        raise ValueError(f"File {data_file} missing required columns {required_cols}")
                    
                    df = df[['Date', 'Weekly_Close']]
                    df['Date'] = pd.to_datetime(df['Date'])
                    df['ticker'] = ticker
                    
                    logger.info(f"Loaded data from {file_path}")
                    data = df
                    
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {str(e)}")
                    raise
        
        if data is None:
            raise ValueError(f"No valid data found for ticker {ticker}")
        
        return data, start_date, end_date
    
    def prepare_data(self, df, test_size=0.2, min_train_size=52):
        """Prepare and split data into train and test sets.
        
        Args:
            df: DataFrame with time series data
            test_size: Proportion of data to use for testing
            min_train_size: Minimum number of observations for training
            
        Returns:
            Tuple of (train_df, test_df)
            
        Raises:
            ValueError: If not enough data points for splitting
        """
        if len(df) < min_train_size + 1:
            raise ValueError(f"Not enough data points for splitting. Need at least {min_train_size + 1}.")
            
        # Sort by date
        df = df.sort_values('Date').reset_index(drop=True)
        
        # Calculate split point with minimum train size
        split_idx = max(int(len(df) * (1 - test_size)), min_train_size)
        
        # Split data
        train_df = df[:split_idx].copy()
        test_df = df[split_idx:].copy()
        
        logger.info(f"Data split: {len(train_df)} training samples, {len(test_df)} test samples")
        
        return train_df, test_df
