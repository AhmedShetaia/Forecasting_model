"""
Pipeline orchestrator for the complete financial data processing system.

This script coordinates the three main components:
1. Data scraping (from scraping/update_all.py)
2. Modeling and prediction (from modelling/update_predictions.py)
3. Forecasting (from forecasting/main.py)
4. Upload results to Azure Blob Storage for easy access
"""

import os
import sys
import logging
import argparse
import datetime
import glob
from dotenv import load_dotenv
from pathlib import Path

# Add project root to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import components from each module
from scraping.update_all import DataUpdater
from modelling.utils.file_utils import save_predictions
from modelling.config.constants import (
    PREDICTIONS_DIR,
    TIMEMOE_CACHE_DIR,
    SCRAPED_DATA_DIR,
)

# Import storage utils (will be created)
from utils.storage_utils import upload_to_blob_storage

# Constants
DEFAULT_BLOB_CONTAINER = "forecast-predictions"
FORECASTING_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "forecasting", "data")


def parse_args():
    """Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='Run the complete financial data pipeline: scraping, modeling, and forecasting'
    )
    
    parser.add_argument(
        '--skip-scraping',
        action='store_true',
        help='Skip the data scraping step'
    )
    
    parser.add_argument(
        '--skip-modeling',
        action='store_true',
        help='Skip the modeling step'
    )
    
    parser.add_argument(
        '--skip-forecasting',
        action='store_true',
        help='Skip the forecasting step'
    )
    
    parser.add_argument(
        '--skip-upload',
        action='store_true',
        help='Skip uploading results to Azure Blob Storage'
    )
    
    parser.add_argument(
        '--container-name',
        type=str,
        default=DEFAULT_BLOB_CONTAINER,
        help=f'Azure Blob container name (default: {DEFAULT_BLOB_CONTAINER})'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Set the logging level'
    )
    
    return parser.parse_args()


def configure_logging(log_level):
    """Configure logging based on provided log level.
    
    Args:
        log_level: Name of the log level (e.g., 'INFO', 'DEBUG')
    """
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f"pipeline_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        ]
    )


def run_scraping():
    """Run the data scraping step."""
    logger = logging.getLogger("pipeline.scraping")
    
    # Get FRED API key from environment
    fred_api_key = os.getenv("FRED_API_KEY")
    
    if not fred_api_key:
        logger.error("FRED_API_KEY not found in environment variables")
        sys.exit(1)
    
    logger.info("Starting data scraping step")
    
    try:
        # Initialize the data updater
        updater = DataUpdater(fred_api_key)
        
        # Run the update process
        updater.update_all_data(include_market=True)
        
        logger.info("Data scraping completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error in scraping step: {str(e)}", exc_info=True)
        return False


def run_modeling():
    """Run the modeling and prediction step."""
    logger = logging.getLogger("pipeline.modeling")
    logger.info("Starting modeling and prediction step")
    
    try:
        # Import here to avoid circular imports
        import modelling.update_predictions as update_predictions
        
        # Parse arguments with defaults
        class Args:
            pred_dir = PREDICTIONS_DIR
            scraped_folder = SCRAPED_DATA_DIR
            cache_dir = TIMEMOE_CACHE_DIR
            ticker = None
            single_file = None
            log_level = logging.getLogger().level
        
        args = Args()
        
        # Configure update predictions logging
        log_level = update_predictions.configure_logging(
            logging.getLevelName(logging.getLogger().level)
        )
        
        # Run update predictions main function
        update_predictions.main()
        
        logger.info("Modeling and prediction completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error in modeling step: {str(e)}", exc_info=True)
        return False


def run_forecasting():
    """Run the forecasting step."""
    logger = logging.getLogger("pipeline.forecasting")
    logger.info("Starting forecasting step")
    
    try:
        # Import the forecasting module
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'forecasting'))
        import forecasting.main as forecasting_main
        
        # Run forecasting main function
        forecasting_main.main()
        
        logger.info("Forecasting completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error in forecasting step: {str(e)}", exc_info=True)
        return False


def find_latest_prediction_file():
    """Find the latest next_friday_predictions JSON file.
    
    Returns:
        Path to the latest prediction file, or None if not found
    """
    logger = logging.getLogger("pipeline.upload")
    
    # Search for next_friday_predictions files
    pattern = os.path.join(FORECASTING_DATA_DIR, "next_friday_predictions_*.json")
    files = glob.glob(pattern)
    
    if not files:
        logger.warning(f"No prediction files found matching pattern: {pattern}")
        return None
    
    # Sort by modification time (newest first)
    latest_file = max(files, key=os.path.getmtime)
    logger.info(f"Found latest prediction file: {latest_file}")
    
    return latest_file


def upload_results_to_blob(container_name):
    """Upload forecasting results to Azure Blob Storage.
    
    Args:
        container_name: Name of the Azure Blob container
        
    Returns:
        URL of the uploaded blob, or None if upload failed
    """
    logger = logging.getLogger("pipeline.upload")
    logger.info("Starting upload of results to Azure Blob Storage")
    
    try:
        # Find the latest prediction file
        latest_file = find_latest_prediction_file()
        
        if not latest_file:
            logger.warning("No prediction file found to upload")
            return None
        
        # Upload the file
        blob_url = upload_to_blob_storage(latest_file, container_name)
        
        if blob_url:
            logger.info(f"Prediction file uploaded successfully to {blob_url}")
            return blob_url
        else:
            logger.error("Failed to upload prediction file")
            return None
            
    except Exception as e:
        logger.error(f"Error uploading results: {str(e)}", exc_info=True)
        return None


def main():
    """Main function to run the complete pipeline."""
    # Parse command line arguments
    args = parse_args()
    
    # Load environment variables from .env file if it exists
    load_dotenv()
    
    # Configure logging
    configure_logging(args.log_level)
    logger = logging.getLogger("pipeline")
    
    logger.info("Starting financial data processing pipeline")
    
    # Track overall pipeline success
    pipeline_success = True
    
    # Run the scraping step if not skipped
    if not args.skip_scraping:
        scraping_success = run_scraping()
        if not scraping_success:
            logger.warning("Scraping step failed, but continuing with pipeline")
            pipeline_success = False
    else:
        logger.info("Skipping scraping step as requested")
    
    # Run the modeling step if not skipped
    if not args.skip_modeling:
        modeling_success = run_modeling()
        if not modeling_success:
            logger.warning("Modeling step failed, but continuing with pipeline")
            pipeline_success = False
    else:
        logger.info("Skipping modeling step as requested")
    
    # Run the forecasting step if not skipped
    if not args.skip_forecasting:
        forecasting_success = run_forecasting()
        if not forecasting_success:
            logger.warning("Forecasting step failed")
            pipeline_success = False
    else:
        logger.info("Skipping forecasting step as requested")
    
    # Upload results to Azure Blob Storage if not skipped
    if not args.skip_upload:
        blob_url = upload_results_to_blob(args.container_name)
        if blob_url:
            logger.info(f"Prediction results available at: {blob_url}")
        else:
            logger.warning("Failed to upload results to Azure Blob Storage")
            pipeline_success = False
    else:
        logger.info("Skipping upload step as requested")
    
    # Report final status
    if pipeline_success:
        logger.info("Pipeline completed successfully")
    else:
        logger.warning("Pipeline completed with errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
