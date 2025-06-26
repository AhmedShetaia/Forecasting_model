"""Train time series forecasting models for a specific company."""
import os
import argparse
import logging
import sys
from datetime import datetime

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
    DEFAULT_LOG_LEVEL
)


def parse_arguments():
    """Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description='Train models for a specific company')
    
    parser.add_argument(
        '--ticker',
        type=str,
        help='Company ticker symbol (e.g., AAPL)',
        required=True
    )
    
    parser.add_argument(
        '--test-run',
        action='store_true',
        help='Run on a small subset of data for testing'
    )
    
    parser.add_argument(
        '--cache-dir',
        type=str,
        default=TIMEMOE_CACHE_DIR,
        help='Directory to cache the TimeMOE model'
    )
    
    parser.add_argument(
        '--scraped-folder',
        type=str,
        default=SCRAPED_DATA_DIR,
        help='Path to scraped data folder'
    )
    
    parser.add_argument(
        '--config-path',
        type=str,
        default=MODEL_CONFIG_PATH,
        help='Path to model configuration JSON'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default=PREDICTIONS_DIR,
        help='Directory to save prediction results'
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
        format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
    )
    
    return log_level


def main():
    """Main function to train and evaluate models."""
    # Parse arguments
    args = parse_arguments()
    
    # Configure logging
    log_level = configure_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Create necessary directories
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Initialize components
    trainer = ModelTrainer(
        config_path=args.config_path,
        cache_dir=args.cache_dir,
        log_level=log_level
    )
    
    processor = DataProcessor(args.scraped_folder)
    
    try:
        # Load company data
        logger.info(f"Loading data for {args.ticker}...")
        data, start_date, end_date = processor.load_company_data(args.ticker)
        
        if data is None:
            logger.error(f"No data found for {args.ticker}")
            return
        
        # Use a smaller subset for test runs
        if args.test_run:
            logger.info("TEST RUN: Using a small subset of data (limited rows)")
            data = data.head(108)  # Use first 108 rows for quick testing
        
        # Prepare data (fixed split for consistency)
        logger.info("Preparing data...")
        train_data = data[:105]  # Fixed split point for consistency
        test_data = data[105:]
        
        # Train and evaluate models
        logger.info("Training and evaluating models (rolling window)...")
        results = trainer.train(train_data, test_data, args.ticker)
        
        # Generate next-week forecast
        logger.info("Generating forecast for next week...")
        next_week_forecast = trainer.forecast_next_week(data, args.ticker)
        
        # Append next-week predictions to results
        results = results.append(next_week_forecast, ignore_index=True)
        
        # Save results
        output_path = os.path.join(args.output_dir, "model_predictions")
        final_path = save_predictions(
            results,
            output_path,
            args.ticker,
            start_date,
            end_date
        )
        
        logger.info(f"Process completed successfully! Results saved to {final_path}")
        
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
