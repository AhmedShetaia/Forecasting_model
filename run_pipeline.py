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
    
    # Get the root logger and clear any existing handlers to avoid duplication
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Create handlers list
    handlers = [logging.StreamHandler()]
    
    # Try to add file handler to both local and shared storage
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file_local = f"pipeline_{timestamp}.log"
    log_file_shared = f"/mnt/fileshare/pipeline_{timestamp}.log"
    
    # Try local file first
    try:
        handlers.append(logging.FileHandler(log_file_local))
        print(f"Logging to local file: {log_file_local}")
    except Exception as e:
        print(f"Warning: Could not create local log file: {e}")
    
    # Try shared storage file
    try:
        os.makedirs("/mnt/fileshare", exist_ok=True)
        handlers.append(logging.FileHandler(log_file_shared))
        print(f"Logging to shared file: {log_file_shared}")
    except Exception as e:
        print(f"Warning: Could not create shared log file: {e}")
    
    if len(handlers) == 1:
        print("Continuing with console logging only")
    
    # Configure logging with available handlers
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers,
        force=True  # Force reconfiguration
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
        
        # Create arguments object manually instead of parsing command line
        class Args:
            pred_dir = str(PREDICTIONS_DIR)
            scraped_folder = str(SCRAPED_DATA_DIR)
            cache_dir = str(TIMEMOE_CACHE_DIR)
            ticker = None
            single_file = None
            log_level = logging.getLogger().level
        
        args = Args()
        
        # Configure update predictions logging
        log_level = update_predictions.configure_logging('INFO')
        mod_logger = logging.getLogger('modelling.update_predictions')
        
        # Call the update process directly without parsing arguments
        from pathlib import Path
        
        # Handle prediction file updates
        pred_dir = Path(args.pred_dir)
        if pred_dir.exists():
            # Process each prediction file
            for csv_path in sorted(pred_dir.glob('model_predictions_*.csv')):
                try:
                    update_predictions.update_predictions_file(str(csv_path), args, log_level)
                except Exception as e:
                    mod_logger.error(f"Error updating {csv_path}: {e}", exc_info=True)
                    # Continue with other files
        else:
            mod_logger.info(f"Prediction directory {pred_dir} does not exist yet - skipping modeling step")
        
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
        
        # Use the data directory from forecasting constants
        forecasting_data_dir = os.path.join(os.path.dirname(__file__), 'forecasting', 'data')
        
        # Run forecasting pipeline function directly
        predictions_path = forecasting_main.run_forecasting_pipeline(
            data_dir=forecasting_data_dir,
            log_level="INFO"
        )
        
        logger.info(f"Forecasting completed successfully. Predictions saved to: {predictions_path}")
        return True
    except Exception as e:
        logger.error(f"Error in forecasting step: {str(e)}", exc_info=True)
        return False


def find_latest_prediction_file():
    """Find the next_friday_predictions JSON file.
    
    Returns:
        Path to the prediction file, or None if not found
    """
    logger = logging.getLogger("pipeline.upload")
    
    # Search for the simplified prediction file
    prediction_file = os.path.join(FORECASTING_DATA_DIR, "next_friday_predictions.json")
    
    if not os.path.exists(prediction_file):
        logger.warning(f"Prediction file not found: {prediction_file}")
        return None
    
    logger.info(f"Found prediction file: {prediction_file}")
    return prediction_file


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
    try:
        # Parse command line arguments
        args = parse_args()
        
        # Load environment variables from .env file if it exists
        load_dotenv()
        
        # Configure logging
        configure_logging(args.log_level)
        logger = logging.getLogger("pipeline")
        
        logger.info("Starting financial data processing pipeline")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Working directory: {os.getcwd()}")
        logger.info(f"Arguments: {args}")
        
        # Check required environment variables
        required_env_vars = ["FRED_API_KEY", "AZURE_STORAGE_CONNECTION_STRING"]
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            sys.exit(1)
        
        logger.info("Environment variables check passed")
        
        # Track overall pipeline success
        pipeline_success = True
        
        # Run the scraping step if not skipped
        if not args.skip_scraping:
            logger.info("Starting scraping step...")
            scraping_success = run_scraping()
            if not scraping_success:
                logger.warning("Scraping step failed, but continuing with pipeline")
                pipeline_success = False
        else:
            logger.info("Skipping scraping step as requested")
        
        # Run the modeling step if not skipped
        if not args.skip_modeling:
            logger.info("Starting modeling step...")
            modeling_success = run_modeling()
            if not modeling_success:
                logger.warning("Modeling step failed, but continuing with pipeline")
                pipeline_success = False
        else:
            logger.info("Skipping modeling step as requested")
        
        # Run the forecasting step if not skipped
        if not args.skip_forecasting:
            logger.info("Starting forecasting step...")
            forecasting_success = run_forecasting()
            if not forecasting_success:
                logger.warning("Forecasting step failed")
                pipeline_success = False
        else:
            logger.info("Skipping forecasting step as requested")
        
        # Upload results to Azure Blob Storage if not skipped
        if not args.skip_upload:
            logger.info("Starting upload step...")
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
            
    except Exception as e:
        print(f"CRITICAL ERROR in main pipeline: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Add early error detection with file share output
    debug_file = "/mnt/fileshare/debug_output.txt"
    
    try:
        # Create debug output file
        os.makedirs("/mnt/fileshare", exist_ok=True)
        
        with open(debug_file, "w") as f:
            f.write("=== PIPELINE DEBUG START ===\n")
            f.write(f"Start time: {datetime.datetime.now()}\n")
            f.write("Starting pipeline initialization...\n")
            f.flush()
        
        print("Starting pipeline initialization...")
        print(f"Debug output will be written to: {debug_file}")
        print(f"Python executable: {sys.executable}")
        print(f"Python version: {sys.version}")
        print(f"Working directory: {os.getcwd()}")
        print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
        
        # Append to debug file
        with open(debug_file, "a") as f:
            f.write(f"Python executable: {sys.executable}\n")
            f.write(f"Python version: {sys.version}\n")
            f.write(f"Working directory: {os.getcwd()}\n")
            f.write(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}\n")
            f.flush()
        
        # Test critical imports early
        print("Testing critical imports...")
        with open(debug_file, "a") as f:
            f.write("Testing critical imports...\n")
            f.flush()
        
        import pandas as pd
        print(f"pandas version: {pd.__version__}")
        with open(debug_file, "a") as f:
            f.write(f"pandas version: {pd.__version__}\n")
            f.flush()
        
        import numpy as np
        print(f"numpy version: {np.__version__}")
        with open(debug_file, "a") as f:
            f.write(f"numpy version: {np.__version__}\n")
            f.flush()
        
        # Test Azure imports
        try:
            from azure.storage.blob import BlobServiceClient
            print("Azure blob storage import: OK")
            with open(debug_file, "a") as f:
                f.write("Azure blob storage import: OK\n")
                f.flush()
        except ImportError as e:
            print(f"Azure blob storage import failed: {e}")
            with open(debug_file, "a") as f:
                f.write(f"Azure blob storage import failed: {e}\n")
                f.flush()
        
        print("All critical imports successful")
        print("Proceeding to main pipeline...")
        
        with open(debug_file, "a") as f:
            f.write("All critical imports successful\n")
            f.write("Proceeding to main pipeline...\n")
            f.flush()
        
        main()
        
        with open(debug_file, "a") as f:
            f.write("=== PIPELINE DEBUG END ===\n")
            f.write(f"End time: {datetime.datetime.now()}\n")
            f.flush()
        
    except Exception as e:
        error_msg = f"FATAL ERROR during initialization: {str(e)}"
        print(error_msg, file=sys.stderr)
        
        # Write error to debug file
        try:
            with open(debug_file, "a") as f:
                f.write(f"\n=== FATAL ERROR ===\n")
                f.write(f"Error: {str(e)}\n")
                import traceback
                f.write(f"Traceback:\n{traceback.format_exc()}\n")
                f.write(f"Error time: {datetime.datetime.now()}\n")
                f.flush()
        except:
            pass  # Don't fail if we can't write debug file
            
        import traceback
        traceback.print_exc()
        sys.exit(1)
