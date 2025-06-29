"""Update prediction files with new data and forecasts."""
import os
import argparse
import logging
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path
import sys
import re

# Add the parent directory to sys.path to allow local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modelling.utils.data_processor import DataProcessor
from modelling.utils.model_trainer import ModelTrainer
from modelling.utils.file_utils import save_predictions
from modelling.config.constants import (
    PREDICTIONS_DIR,
    TIMEMOE_CACHE_DIR,
    SCRAPED_DATA_DIR,
    MODEL_CONFIG_PATH,
    DEFAULT_LOG_LEVEL,
    DATE_FORMAT
)


def parse_arguments():
    """Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description='Update prediction files with new data')
    
    parser.add_argument(
        '--pred-dir',
        type=str,
        default=PREDICTIONS_DIR,
        help='Directory containing prediction CSVs'
    )
    
    parser.add_argument(
        '--scraped-folder',
        type=str,
        default=SCRAPED_DATA_DIR,
        help='Path to folder containing scraped data'
    )
    
    parser.add_argument(
        '--cache-dir',
        type=str,
        default=TIMEMOE_CACHE_DIR,
        help='Directory to cache the TimeMOE model'
    )
    
    parser.add_argument(
        '--ticker',
        type=str,
        help='Force ticker symbol (optional)',
        default=None
    )
    
    parser.add_argument(
        '--single-file',
        type=str,
        help='Path to a specific prediction file to update (optional)',
        default=None
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        default=DEFAULT_LOG_LEVEL,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Set the logging level'
    )
    
    return parser.parse_args()


def configure_logging(log_level_name):
    """Configure logging based on provided log level.
    
    Args:
        log_level_name: Name of the log level (e.g., 'INFO', 'DEBUG')
        
    Returns:
        Configured log level
    """
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    return log_level


def derive_ticker(pred_file):
    """Extract ticker symbol from prediction filename.
    
    Args:
        pred_file: Path to prediction file
        
    Returns:
        Ticker symbol
        
    Raises:
        ValueError: If ticker cannot be inferred from filename
    """
    # Extract from model_predictions_YYYYMMDD_HHMMSS_TICKER_YYYYMMDD_YYYYMMDD.csv
    filename = Path(pred_file).name
    pattern = r'model_predictions_\d{8}_\d{6}_([A-Z]+)_\d{8}_\d{8}\.csv'
    match = re.match(pattern, filename)
    
    if match:
        return match.group(1)
    
    raise ValueError(f"Unable to infer ticker from file name: {filename}")


def load_existing_predictions(pred_path):
    """Load and prepare existing predictions.
    
    Args:
        pred_path: Path to predictions CSV file
        
    Returns:
        DataFrame with predictions
    """
    df = pd.read_csv(pred_path)
    df['Date'] = pd.to_datetime(df['Date'])
    return df


def update_predictions_file(pred_file, args, log_level):
    """Update a single predictions file with new data and forecasts.
    
    Args:
        pred_file: Path to predictions file
        args: Command line arguments
        log_level: Logging level
        
    Returns:
        Path to updated predictions file, or None if update wasn't needed
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Updating {pred_file}")
    
    # Load existing predictions
    old_pred = load_existing_predictions(pred_file)
    
    if 'actual' not in old_pred.columns:
        raise ValueError(f"Column 'actual' not found in {pred_file}")
    
    # Find the last valid actuals row
    cut_idx = old_pred['actual'].last_valid_index()
    if cut_idx is None:
        logger.warning(f"No non-null 'actual' values found in {pred_file}; skipping")
        return None
    
    # Get the date of the last actual observation
    start_date = old_pred.loc[cut_idx, 'Date']
    
    # Determine ticker and load new data
    ticker = args.ticker or derive_ticker(pred_file)
    logger.info(f"Extracted ticker symbol: {ticker}")
    processor = DataProcessor(args.scraped_folder)
    
    try:
        data, _, end_date = processor.load_company_data(ticker)
    except ValueError as e:
        logger.error(f"Failed to load data for ticker {ticker}: {e}")
        logger.info(f"Checking if scraped data folder exists at: {args.scraped_folder}")
        # List available ticker folders for debugging
        if os.path.exists(args.scraped_folder):
            available_tickers = [folder.name for folder in Path(args.scraped_folder).iterdir() if folder.is_dir()]
            logger.info(f"Available ticker folders: {available_tickers}")
        else:
            logger.error(f"Scraped data folder does not exist: {args.scraped_folder}")
        raise
    
    # Identify new rows following the last actual observation
    new_mask = data['Date'] > start_date
    if not new_mask.any():
        logger.info(f"No new data for {ticker} after {start_date.date()}")
        return None
    
    # Split data for training and testing
    train_data = data[data['Date'] <= start_date].copy()
    test_data = data[new_mask].copy()
    
    # Initialize trainer and generate new predictions
    trainer = ModelTrainer(cache_dir=args.cache_dir, log_level=log_level)
    new_results = trainer.train(train_data, test_data, ticker)
    
    # Generate next-week forecast using all available data
    clean_data = data.dropna(subset=['Weekly_Close'])
    next_week_row = trainer.forecast_next_week(clean_data, ticker)
    
    # Combine existing valid data with new predictions and forecast
    updated_pred = pd.concat([
        old_pred.iloc[: cut_idx + 1],  # Keep existing valid data
        new_results,                   # Add new predictions
        pd.DataFrame([next_week_row])  # Add next week forecast
    ], ignore_index=True)
    
    # Save updated predictions with a new filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    start_str = old_pred['Date'].min().strftime(DATE_FORMAT)
    end_str = test_data['Date'].max().strftime(DATE_FORMAT)
    
    new_filename = f"model_predictions_{timestamp}_{ticker}_{start_str}_{end_str}.csv"
    new_path = os.path.join(os.path.dirname(pred_file), new_filename)
    
    updated_pred.to_csv(new_path, index=False)
    logger.info(f"Saved updated predictions to {new_path}")
    
    # Clean up old predictions file
    try:
        os.remove(pred_file)
        logger.info(f"Removed old predictions file {pred_file}")
    except OSError as e:
        logger.warning(f"Could not delete old file {pred_file}: {e}")
    
    return new_path


def main(args=None):
    """Main function to update prediction files."""
    # Parse arguments
    if args is None:
        args = parse_arguments()
    
    # Configure logging
    log_level = configure_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Handle single file update if specified
    if args.single_file:
        if not os.path.exists(args.single_file):
            logger.error(f"Specified file {args.single_file} does not exist")
            return
            
        try:
            update_predictions_file(args.single_file, args, log_level)
        except Exception as e:
            logger.error(f"Error updating {args.single_file}: {e}", exc_info=True)
        return
    
    # Otherwise, update all prediction files in directory
    pred_dir = Path(args.pred_dir)
    if not pred_dir.exists():
        logger.error(f"Prediction directory {pred_dir} does not exist")
        return
    
    # Process each prediction file
    for csv_path in sorted(pred_dir.glob('model_predictions_*.csv')):
        try:
            update_predictions_file(str(csv_path), args, log_level)
        except Exception as e:
            logger.error(f"Error updating {csv_path}: {e}", exc_info=True)
            # Continue with other files


if __name__ == '__main__':
    main()
