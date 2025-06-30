"""
Pipeline orchestrator for the complete financial data processing system.

This script coordinates the three main components:
1. Data scraping (from scraping/update_all.py)
2. Modeling and prediction (from modelling/update_predictions.py)
3. Forecasting (from forecasting/main.py)
4. Upload results to Azure Blob Storage for easy access

Note: This simplified version relies on selective symlinks for data persistence.
Data directories are symlinked to Azure File Share while source code stays in container.
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
    CACHE_DIR
)

# Import storage utils (will be created)
from utils.storage_utils import upload_to_blob_storage

# Constants
DEFAULT_BLOB_CONTAINER = "forecast-predictions"


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
    
    # Try to add file handler to both local and persistent storage
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file_local = f"pipeline_{timestamp}.log"
    log_file_persistent = f"logs/pipeline_{timestamp}.log"
    
    # Try local file first
    try:
        handlers.append(logging.FileHandler(log_file_local))
        print(f"Logging to local file: {log_file_local}")
    except Exception as e:
        print(f"Warning: Could not create local log file: {e}")
    
    # Try persistent storage file (via potential symlink)
    try:
        os.makedirs("logs", exist_ok=True)
        handlers.append(logging.FileHandler(log_file_persistent))
        print(f"Logging to persistent file: {log_file_persistent}")
    except Exception as e:
        print(f"Warning: Could not create persistent log file: {e}")
    
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
        # Initialize the data updater (will use symlinked directories automatically)
        updater = DataUpdater(fred_api_key)
        
        # Run the update process - data will be saved via symlinks to file share
        updater.update_all_data(include_market=True)
        
        logger.info("Data scraping completed successfully")
        logger.info("Scraped data saved via symlinks to persistent storage")
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
        
        logger.info("Using symlinked directories for modeling")
        
        # Check for existing prediction files (through symlinks)
        existing_files = list(Path(PREDICTIONS_DIR).glob('model_predictions_*.csv'))
        logger.info(f"Found {len(existing_files)} existing prediction files:")
        for file in existing_files:
            logger.info(f"  - {file.name}")
        
        # Check for existing scraped data (through symlinks)
        scraped_data_files = []
        if os.path.exists(SCRAPED_DATA_DIR):
            scraped_data_files = [f for f in os.listdir(SCRAPED_DATA_DIR) 
                                if os.path.isdir(os.path.join(SCRAPED_DATA_DIR, f))]
        logger.info(f"Found {len(scraped_data_files)} scraped data folders: {scraped_data_files}")
        
        # Create arguments object using constants (symlinked paths)
        class Args:
            def __init__(self):
                self.pred_dir = str(PREDICTIONS_DIR)
                self.scraped_folder = str(SCRAPED_DATA_DIR)
                self.cache_dir = str(CACHE_DIR)
                self.ticker = None
                self.single_file = None
                self.log_level = logging.getLogger().level
        
        args = Args()
        
        # Configure update predictions logging
        log_level = update_predictions.configure_logging('INFO')
        mod_logger = logging.getLogger('modelling.update_predictions')
        
        # Run predictions update if there's data
        if existing_files and scraped_data_files:
            mod_logger.info("Found existing predictions and scraped data - updating predictions")
            update_predictions.main(args)
        elif scraped_data_files:
            mod_logger.info(f"Found scraped data but no prediction files. Consider running model training.")
            mod_logger.info("Skipping modeling step - no existing prediction files to update")
            return False
        else:
            mod_logger.info("No existing prediction files or scraped data found - skipping modeling step")
            return False
        
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
        # Check for prediction files (through symlinked directories)
        pred_files = list(Path(PREDICTIONS_DIR).glob('model_predictions_*.csv'))
        if not pred_files:
            logger.error(f"No prediction files found in: {PREDICTIONS_DIR}")
            return False
        
        logger.info(f"Found {len(pred_files)} prediction files for forecasting")
        
        # Import forecasting components
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'forecasting'))
        import forecasting.main as forecasting_main
        
        # Run forecasting (will use symlinked data directories)
        logger.info("Running forecasting pipeline with symlinked data")
        predictions_path = forecasting_main.run_forecasting_pipeline(
            log_level="INFO"
        )
        
        logger.info(f"Forecasting completed successfully. Results: {predictions_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error in forecasting step: {str(e)}", exc_info=True)
        return False


def get_output_files():
    """Get list of output files for upload.
    
    Returns:
        List of file paths to upload
    """
    logger = logging.getLogger("pipeline.upload")
    
    # Use constants to find output files through symlinks
    from forecasting.src.config.constants import DEFAULT_DATA_DIR
    
    output_files = []
    
    # Find forecasting output files
    forecasting_data_pattern = os.path.join(DEFAULT_DATA_DIR, "next_friday_predictions_*.json")
    prediction_files = glob.glob(forecasting_data_pattern)
    
    # Also check for the main prediction file
    main_prediction_file = os.path.join(DEFAULT_DATA_DIR, "next_friday_predictions.json")
    if os.path.exists(main_prediction_file):
        prediction_files.append(main_prediction_file)
    
    for file_path in prediction_files:
        if os.path.exists(file_path):
            output_files.append(file_path)
            logger.info(f"Found output file: {file_path}")
    
    # Find all JSON files in forecasting data directory
    if os.path.exists(DEFAULT_DATA_DIR):
        json_files = glob.glob(os.path.join(DEFAULT_DATA_DIR, "*.json"))
        for json_file in json_files:
            if json_file not in output_files:
                output_files.append(json_file)
                logger.info(f"Found additional JSON file: {json_file}")
    
    if not output_files:
        logger.warning(f"No prediction files found in: {DEFAULT_DATA_DIR}")
        logger.info("No output files to upload")
        
    return output_files


def upload_results_to_blob(container_name, output_files):
    """Upload results to Azure Blob Storage.
    
    Args:
        container_name: Name of the Azure Blob container
        output_files: List of file paths to upload
        
    Returns:
        bool: True if upload successful, False otherwise
    """
    logger = logging.getLogger("pipeline.upload")
    
    if not output_files:
        logger.info("No output files to upload")
        return True
    
    try:
        logger.info(f"Uploading {len(output_files)} files to Azure Blob Storage")
        
        # Get Azure connection string from environment
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not connection_string:
            logger.error("AZURE_STORAGE_CONNECTION_STRING not found in environment variables")
            return False
        
        upload_count = 0
        for file_path in output_files:
            try:
                # Extract filename for blob name
                blob_name = os.path.basename(file_path)
                
                # Add timestamp prefix to avoid overwrites
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                blob_name_with_timestamp = f"{timestamp}_{blob_name}"
                
                # Upload to blob storage
                success = upload_to_blob_storage(
                    file_path=file_path,
                    blob_name=blob_name_with_timestamp,
                    container_name=container_name,
                    connection_string=connection_string
                )
                
                if success:
                    upload_count += 1
                    logger.info(f"✓ Uploaded: {file_path} -> {blob_name_with_timestamp}")
                else:
                    logger.error(f"✗ Failed to upload: {file_path}")
                    
            except Exception as e:
                logger.error(f"Error uploading {file_path}: {str(e)}")
        
        logger.info(f"Upload completed: {upload_count}/{len(output_files)} files uploaded successfully")
        return upload_count == len(output_files)
        
    except Exception as e:
        logger.error(f"Error in upload process: {str(e)}", exc_info=True)
        return False


def verify_symlinks():
    """Verify that data symlinks are properly set up.
    
    Returns:
        bool: True if all symlinks are working, False otherwise
    """
    logger = logging.getLogger("pipeline.init")
    
    # Check if we're running in a container with symlinks
    symlink_base = "/mnt/fileshare"
    if not os.path.exists(symlink_base):
        logger.info("Not running in Azure File Share environment - using local directories")
        return True
    
    # Expected symlinked directories
    symlinked_dirs = [
        "forecasting/data",
        "modelling/cache",
        "modelling/predictions", 
        "scraping/scraped_data",
        "logs"
    ]
    
    all_good = True
    for dir_path in symlinked_dirs:
        if os.path.islink(dir_path) and os.path.exists(dir_path):
            target = os.readlink(dir_path)
            logger.info(f"✓ Symlink verified: {dir_path} -> {target}")
        elif os.path.exists(dir_path):
            logger.info(f"? Directory exists (not symlinked): {dir_path}")
        else:
            logger.warning(f"✗ Missing directory/symlink: {dir_path}")
            all_good = False
    
    return all_good


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
        
        # Verify symlinks if in container environment
        if not verify_symlinks():
            logger.warning("Some symlinks may not be set up correctly")
        
        logger.info("🚀 Starting Financial Data Pipeline")
        logger.info("=" * 50)
        
        # Track success of each step
        steps_completed = []
        steps_failed = []
        
        # Step 1: Data Scraping
        if not args.skip_scraping:
            logger.info("📊 Step 1: Data Scraping")
            logger.info("-" * 30)
            
            try:
                if run_scraping():
                    steps_completed.append("Data Scraping")
                    logger.info("✅ Data scraping completed successfully")
                else:
                    steps_failed.append("Data Scraping")
                    logger.error("❌ Data scraping failed")
            except Exception as e:
                steps_failed.append("Data Scraping")
                logger.error(f"❌ Data scraping failed with exception: {str(e)}")
        else:
            logger.info("⏭️  Skipping data scraping (--skip-scraping)")
        
        # Step 2: Modeling and Prediction
        if not args.skip_modeling:
            logger.info("\n🧠 Step 2: Modeling and Prediction")
            logger.info("-" * 35)
            
            try:
                if run_modeling():
                    steps_completed.append("Modeling")
                    logger.info("✅ Modeling completed successfully")
                else:
                    steps_failed.append("Modeling")
                    logger.warning("⚠️  Modeling step skipped or failed")
            except Exception as e:
                steps_failed.append("Modeling")
                logger.error(f"❌ Modeling failed with exception: {str(e)}")
        else:
            logger.info("⏭️  Skipping modeling (--skip-modeling)")
        
        # Step 3: Forecasting
        if not args.skip_forecasting:
            logger.info("\n🔮 Step 3: Forecasting")
            logger.info("-" * 25)
            
            try:
                if run_forecasting():
                    steps_completed.append("Forecasting")
                    logger.info("✅ Forecasting completed successfully")
                else:
                    steps_failed.append("Forecasting")
                    logger.error("❌ Forecasting failed")
            except Exception as e:
                steps_failed.append("Forecasting")
                logger.error(f"❌ Forecasting failed with exception: {str(e)}")
        else:
            logger.info("⏭️  Skipping forecasting (--skip-forecasting)")
        
        # Step 4: Upload Results
        if not args.skip_upload:
            logger.info("\n☁️  Step 4: Upload Results to Azure Blob Storage")
            logger.info("-" * 45)
            
            try:
                output_files = get_output_files()
                if upload_results_to_blob(args.container_name, output_files):
                    steps_completed.append("Upload")
                    logger.info("✅ Upload completed successfully")
                else:
                    steps_failed.append("Upload")
                    logger.error("❌ Upload failed")
            except Exception as e:
                steps_failed.append("Upload")
                logger.error(f"❌ Upload failed with exception: {str(e)}")
        else:
            logger.info("⏭️  Skipping upload (--skip-upload)")
        
        # Final Summary
        logger.info("\n" + "=" * 50)
        logger.info("🏁 Pipeline Summary")
        logger.info("=" * 50)
        
        if steps_completed:
            logger.info(f"✅ Completed steps: {', '.join(steps_completed)}")
        
        if steps_failed:
            logger.error(f"❌ Failed steps: {', '.join(steps_failed)}")
            sys.exit(1)
        else:
            logger.info("🎉 All pipeline steps completed successfully!")
            
    except KeyboardInterrupt:
        logger.info("⏸️  Pipeline interrupted by user")
        sys.exit(130)  # Standard exit code for Ctrl+C
    except Exception as e:
        logger.error(f"💥 Unexpected error in pipeline: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
