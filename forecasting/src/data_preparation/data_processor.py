"""
Data processor for preparing forecasting model inputs.
"""

import os
import glob
import logging
import pandas as pd
from typing import Optional, List, Dict, Any, Union, Tuple

from ..config.constants import (
    DEFAULT_OUTPUT_DIR, DEFAULT_PREDICTIONS_DIR,
    DATE_FORMAT, MARKET_DATA_DIR_PATTERN, MARKET_DATA_FILENAME
)

# Configure module logger
logger = logging.getLogger(__name__)

class DataProcessor:
    """
    Processor for preparing and combining prediction data with market data.
    """
    
    def __init__(self, 
                 predictions_dir: Optional[str] = None,
                 market_data_dir: Optional[str] = None,
                 output_path: Optional[str] = None):
        """
        Initialize the DataProcessor.
        
        Args:
            predictions_dir: Directory containing prediction CSV files
            market_data_dir: Directory containing market data files (defaults to scraping/scraped_data)
            output_path: Directory to save output files (defaults to 'forecasting/data/output')
        """
        # Default paths that will be overridden if provided
        self.predictions_dir = predictions_dir or DEFAULT_PREDICTIONS_DIR
        self.market_data_dir = market_data_dir or "scraping/scraped_data"
        self.output_path = output_path or DEFAULT_OUTPUT_DIR
        
    def _find_prediction_files(self) -> List[str]:
        """
        Find all prediction CSV files in the predictions directory.
        
        Returns:
            List of prediction file paths
            
        Raises:
            FileNotFoundError: If predictions directory or files are not found
        """
        # Use project root instead of current file location
        project_root = os.getcwd()
        
        if os.path.isabs(self.predictions_dir):
            predictions_path = self.predictions_dir
        else:
            predictions_path = os.path.join(project_root, self.predictions_dir)
        
        predictions_path = os.path.normpath(predictions_path)
        
        if not os.path.exists(predictions_path):
            logger.error(f"Predictions directory does not exist: {predictions_path}")
            raise FileNotFoundError(f"Predictions directory not found at: {predictions_path}")
        
        prediction_files = glob.glob(os.path.join(predictions_path, "*.csv"))
        
        if not prediction_files:
            logger.error(f"No prediction files found in {predictions_path}")
            raise FileNotFoundError(f"No prediction files found in {predictions_path}")
            
        logger.info(f"Found {len(prediction_files)} prediction files")
        return prediction_files
    
    def _load_market_data(self) -> pd.DataFrame:
        """
        Load market data from the most recent market data directory.
        Finds the latest market_data_YYYYMMDD_YYYYMMDD directory and loads the market_data.csv file.
        
        Returns:
            DataFrame with market data
            
        Raises:
            FileNotFoundError: If market data file is not found
        """
        try:
            # Use project root instead of current file location
            project_root = os.getcwd()
            
            if os.path.isabs(self.market_data_dir):
                base_data_dir = self.market_data_dir
            else:
                base_data_dir = os.path.join(project_root, self.market_data_dir)
            
            base_data_dir = os.path.normpath(base_data_dir)
            
            # Find all market data directories
            market_data_dirs = glob.glob(os.path.join(base_data_dir, MARKET_DATA_DIR_PATTERN))
            
            if not market_data_dirs:
                raise FileNotFoundError(f"No market data directories found matching pattern {MARKET_DATA_DIR_PATTERN} in {base_data_dir}")
            
            # Sort by the end date in directory name (descending)
            # Assuming directory format: market_data_YYYYMMDD_YYYYMMDD
            market_data_dirs.sort(key=lambda x: x.split('_')[-1], reverse=True)
            
            # Get the latest directory
            latest_market_dir = market_data_dirs[0]
            logger.debug(f"Using latest market data directory: {latest_market_dir}")
            
            # Construct path to market_data.csv
            market_data_path = os.path.join(latest_market_dir, MARKET_DATA_FILENAME)
            
            if not os.path.exists(market_data_path):
                raise FileNotFoundError(f"{MARKET_DATA_FILENAME} not found in {latest_market_dir}")
                
            logger.info(f"Reading market data from {market_data_path}")
            return pd.read_csv(market_data_path)
            
        except FileNotFoundError as e:
            logger.error(f"Market data file not found: {str(e)}")
            raise
    
    def _combine_predictions(self, prediction_files: List[str]) -> pd.DataFrame:
        """
        Combine multiple prediction files into a single DataFrame.
        
        Args:
            prediction_files: List of paths to prediction CSV files
            
        Returns:
            Combined DataFrame of all predictions
        """
        dfs = []
        for file in prediction_files:
            logger.debug(f"Reading: {os.path.basename(file)}")
            df = pd.read_csv(file)
            dfs.append(df)
            
        logger.info("Combining prediction files...")
        return pd.concat(dfs, ignore_index=True)
    
    def _merge_with_market_data(self, 
                               predictions: pd.DataFrame, 
                               market_data: pd.DataFrame) -> pd.DataFrame:
        """
        Merge prediction data with market data using a weekly lag.
        
        Args:
            predictions: DataFrame containing model predictions
            market_data: DataFrame containing market data
            
        Returns:
            Merged DataFrame with predictions and corresponding market data
        """
        logger.info("Converting date formats and preparing for weekly lag merge...")
        
        # Ensure date columns are datetime type
        predictions['Date'] = pd.to_datetime(predictions['Date'])
        market_data['Date'] = pd.to_datetime(market_data['Date'])
        
        # Create a new column for the market data date (one week before prediction)
        predictions['MarketDate'] = predictions['Date'] - pd.Timedelta(days=7)
        
        # Merge using MarketDate from predictions and Date from market data
        final_data = pd.merge(
            predictions,
            market_data,
            left_on='MarketDate',
            right_on='Date',
            how='left',
            suffixes=('', '_market')
        )
        
        # Drop the extra Date columns
        final_data = final_data.drop(columns=['MarketDate', 'Date_market'])
        
        return final_data
    
    def _get_second_latest_date(self, df: pd.DataFrame) -> str:
        """
        Get the second latest date from a DataFrame with a 'Date' column.
        
        Args:
            df: DataFrame with a 'Date' column
            
        Returns:
            Second latest date in YYYYMMDD format
        """
        sorted_dates = df['Date'].sort_values().unique()
        
        if len(sorted_dates) >= 2:
            second_latest_date = pd.to_datetime(sorted_dates[-2]).strftime(DATE_FORMAT)
        else:
            second_latest_date = pd.to_datetime(sorted_dates[-1]).strftime(DATE_FORMAT)
            
        return second_latest_date
    
    def prepare_data(self, save_output: bool = True) -> pd.DataFrame:
        """
        Read all model predictions from the predictions folder,
        combine them into one file, then merge with market data on Date column.
        The output file will include the second latest date in its filename.
        
        Args:
            save_output: Whether to save the combined data to a CSV file
            
        Returns:
            The combined dataset with predictions and market data
        """
        logger.info("Starting data preparation...")
        
        # Load and combine prediction data
        prediction_files = self._find_prediction_files()
        combined_predictions = self._combine_predictions(prediction_files)
        
        # Load market data
        market_data = self._load_market_data()
        
        # Merge predictions with market data
        final_data = self._merge_with_market_data(combined_predictions, market_data)
        
        # Optionally save the output
        if save_output:
            # Clean up old combined_data files before saving new one
            from ..utils.file_utils import clean_old_files
            clean_old_files(self.output_path, "combined_data_until_*.csv")
            
            second_latest_date = self._get_second_latest_date(final_data)
            output_filename = f"combined_data_until_{second_latest_date}.csv"
            output_file_path = os.path.join(self.output_path, output_filename)
            
            # Create directory if it doesn't exist
            os.makedirs(self.output_path, exist_ok=True)
            
            logger.info(f"Saving combined data to {output_file_path}...")
            final_data.to_csv(output_file_path, index=False)
        
        logger.info("Data preparation complete!")
        logger.info(f"Final dataset shape: {final_data.shape}")
        
        return final_data
