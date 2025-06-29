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

# Azure File Share paths - AFS only (using same structure as imported constants)
AFS_BASE = "/mnt/fileshare"
AFS_PREDICTIONS_DIR = f"{AFS_BASE}/modelling/predictions"
AFS_CACHE_DIR = f"{AFS_BASE}/modelling/cache"
AFS_SCRAPED_DATA_DIR = f"{AFS_BASE}/scraping/scraped_data"
AFS_TIMEMOE_CACHE_DIR = f"{AFS_BASE}/modelling/cache/time_moe_cache"
AFS_FORECASTING_DIR = f"{AFS_BASE}/forecasting"
AFS_SCRAPING_DIR = f"{AFS_BASE}/scraping"
FORECASTING_DATA_DIR = f"{AFS_FORECASTING_DIR}/data"


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
    """Run the data scraping step using Azure File Share."""
    logger = logging.getLogger("pipeline.scraping")
    
    # Ensure AFS scraped data directory exists
    os.makedirs(AFS_SCRAPED_DATA_DIR, exist_ok=True)
    
    # Get FRED API key from environment
    fred_api_key = os.getenv("FRED_API_KEY")
    
    if not fred_api_key:
        logger.error("FRED_API_KEY not found in environment variables")
        sys.exit(1)
    
    logger.info("Starting data scraping step")
    logger.info(f"Using AFS scraped data directory: {AFS_SCRAPED_DATA_DIR}")
    
    try:
        # Initialize the data updater with AFS-compatible configuration
        updater = DataUpdater(fred_api_key)
        
        # Set the scraped data directory to AFS location
        # This ensures all scraped data goes to Azure File Share
        original_scraped_dir = getattr(updater, 'scraped_data_dir', None)
        if hasattr(updater, 'scraped_data_dir'):
            updater.scraped_data_dir = AFS_SCRAPED_DATA_DIR
        
        # Run the update process - this will now save to AFS
        updater.update_all_data(include_market=True)
        
        # Restore original directory if it was changed
        if original_scraped_dir and hasattr(updater, 'scraped_data_dir'):
            updater.scraped_data_dir = original_scraped_dir
        
        logger.info("Data scraping completed successfully")
        logger.info(f"Scraped data saved to AFS: {AFS_SCRAPED_DATA_DIR}")
        return True
    except Exception as e:
        logger.error(f"Error in scraping step: {str(e)}", exc_info=True)
        return False


def run_modeling():
    """Run the modeling and prediction step using Azure File Share."""
    logger = logging.getLogger("pipeline.modeling")
    logger.info("Starting modeling and prediction step")
    
    try:
        # Import here to avoid circular imports
        import modelling.update_predictions as update_predictions
        
        # Use only AFS paths
        predictions_dir = AFS_PREDICTIONS_DIR
        cache_dir = AFS_CACHE_DIR
        
        logger.info(f"Using Azure File Share predictions directory: {predictions_dir}")
        logger.info(f"Using Azure File Share cache directory: {cache_dir}")
        
        # Verify AFS is mounted and accessible
        if not os.path.exists(AFS_BASE):
            raise FileNotFoundError(f"Azure File Share not mounted at {AFS_BASE}")
        
        # Ensure directories exist in AFS
        os.makedirs(predictions_dir, exist_ok=True)
        os.makedirs(cache_dir, exist_ok=True)
        os.makedirs(AFS_SCRAPED_DATA_DIR, exist_ok=True)
        os.makedirs(f"{cache_dir}/sarima_params", exist_ok=True)
        os.makedirs(f"{cache_dir}/time_moe_cache", exist_ok=True)
        
        # Check for existing prediction files in AFS
        existing_files = list(Path(predictions_dir).glob('model_predictions_*.csv'))
        logger.info(f"Found {len(existing_files)} prediction files in AFS:")
        for file in existing_files:
            logger.info(f"  - {file.name}")
        
        # Check for existing scraped data in AFS
        scraped_data_files = []
        if os.path.exists(AFS_SCRAPED_DATA_DIR):
            scraped_data_files = [f for f in os.listdir(AFS_SCRAPED_DATA_DIR) 
                                if os.path.isdir(os.path.join(AFS_SCRAPED_DATA_DIR, f))]
        logger.info(f"Found {len(scraped_data_files)} scraped data folders in AFS: {scraped_data_files}")
        
        # Create arguments object pointing to AFS paths
        class Args:
            def __init__(self):
                self.pred_dir = predictions_dir
                self.scraped_folder = AFS_SCRAPED_DATA_DIR  # Use AFS path instead of imported SCRAPED_DATA_DIR
                self.cache_dir = cache_dir
                self.ticker = None
                self.single_file = None
                self.log_level = logging.getLogger().level
        
        args = Args()
        
        # Configure update predictions logging
        log_level = update_predictions.configure_logging('INFO')
        mod_logger = logging.getLogger('modelling.update_predictions')
        
        if existing_files:
            # Update existing prediction files in AFS
            mod_logger.info(f"Updating {len(existing_files)} existing prediction files in AFS")
            for csv_path in sorted(existing_files):
                try:
                    mod_logger.info(f"Updating predictions file: {csv_path.name}")
                    update_predictions.update_predictions_file(str(csv_path), args, log_level)
                    mod_logger.info(f"Successfully updated: {csv_path.name}")
                except Exception as e:
                    mod_logger.error(f"Error updating {csv_path}: {e}", exc_info=True)
                    # Continue with other files
            return True
        elif scraped_data_files:
            # If we have scraped data but no prediction files, we could generate new ones
            mod_logger.info(f"Found scraped data but no prediction files. Consider running model training.")
            mod_logger.info("Skipping modeling step - no existing prediction files to update")
            return False
        else:
            mod_logger.info("No existing prediction files or scraped data found in AFS - skipping modeling step")
            return False
        
        logger.info("Modeling and prediction completed successfully using AFS")
        return True
        
    except Exception as e:
        logger.error(f"Error in modeling step: {str(e)}", exc_info=True)
        return False


def run_forecasting():
    """Run the forecasting step using Azure File Share."""
    logger = logging.getLogger("pipeline.forecasting")
    logger.info("Starting forecasting step using AFS")
    
    try:
        # Use only AFS paths
        predictions_dir = AFS_PREDICTIONS_DIR
        forecasting_dir = AFS_FORECASTING_DIR
        
        # Verify prediction files exist in AFS
        if not os.path.exists(predictions_dir):
            logger.error(f"AFS predictions directory not found: {predictions_dir}")
            return False
        
        pred_files = list(Path(predictions_dir).glob('model_predictions_*.csv'))
        if not pred_files:
            logger.error(f"No prediction files found in AFS: {predictions_dir}")
            return False
        
        logger.info(f"Found {len(pred_files)} prediction files in AFS for forecasting")
        
        # Ensure forecasting directory exists in AFS
        os.makedirs(forecasting_dir, exist_ok=True)
        os.makedirs(FORECASTING_DATA_DIR, exist_ok=True)
        
        # Import forecasting components
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'forecasting'))
        import forecasting.main as forecasting_main
        
        # Temporarily modify the DEFAULT_PREDICTIONS_DIR to point to AFS
        import forecasting.src.config.constants as constants
        original_predictions_dir = constants.DEFAULT_PREDICTIONS_DIR
        constants.DEFAULT_PREDICTIONS_DIR = predictions_dir
        
        try:
            # Run forecasting with AFS data, save to AFS
            logger.info(f"Running forecasting with predictions from AFS: {predictions_dir}")
            predictions_path = forecasting_main.run_forecasting_pipeline(
                data_dir=FORECASTING_DATA_DIR,
                log_level="INFO"
            )
            
            logger.info(f"Forecasting completed successfully. Results saved to AFS: {predictions_path}")
            return True
            
        finally:
            # Restore original predictions directory
            constants.DEFAULT_PREDICTIONS_DIR = original_predictions_dir
        
    except Exception as e:
        logger.error(f"Error in forecasting step: {str(e)}", exc_info=True)
        return False


def find_latest_prediction_file():
    """Find the next_friday_predictions JSON file in AFS.
    
    Returns:
        Path to the prediction file, or None if not found
    """
    logger = logging.getLogger("pipeline.upload")
    
    # Search for prediction files in AFS forecasting data directory
    prediction_file = os.path.join(FORECASTING_DATA_DIR, "next_friday_predictions.json")
    
    # Also check for timestamped prediction files
    forecasting_data_pattern = os.path.join(FORECASTING_DATA_DIR, "next_friday_predictions_*.json")
    timestamped_files = glob.glob(forecasting_data_pattern)
    
    # Use the timestamped file if available, otherwise use the simple one
    if timestamped_files:
        # Sort by modification time and get the latest
        latest_timestamped = max(timestamped_files, key=os.path.getmtime)
        logger.info(f"Found timestamped prediction file: {latest_timestamped}")
        return latest_timestamped
    elif os.path.exists(prediction_file):
        logger.info(f"Found prediction file: {prediction_file}")
        return prediction_file
    else:
        # Search for any JSON files in the forecasting data directory
        json_files = glob.glob(os.path.join(FORECASTING_DATA_DIR, "*.json"))
        if json_files:
            latest_json = max(json_files, key=os.path.getmtime)
            logger.info(f"Found latest JSON file: {latest_json}")
            return latest_json
        
        logger.warning(f"No prediction files found in AFS: {FORECASTING_DATA_DIR}")
        return None


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


def debug_afs_only():
    """Debug function to show AFS contents and verify compatibility."""
    logger = logging.getLogger("pipeline.debug")
    
    try:
        afs_base = AFS_BASE
        if not os.path.exists(afs_base):
            logger.error(f"❌ Azure File Share not mounted at {afs_base}")
            logger.error("Please check Docker volume mount or Azure File Share configuration")
            return False
            
        logger.info("✅ Azure File Share mounted successfully")
        
        # Test basic read/write operations
        try:
            test_file = os.path.join(afs_base, "afs_test.tmp")
            with open(test_file, "w") as f:
                f.write("AFS compatibility test")
            
            with open(test_file, "r") as f:
                content = f.read()
            
            os.remove(test_file)
            logger.info("✅ AFS read/write operations working")
        except Exception as e:
            logger.error(f"❌ AFS read/write test failed: {e}")
            return False
        
        logger.info("=== AZURE FILE SHARE CONTENTS ===")
        
        total_files = 0
        total_size = 0
        
        for root, dirs, files in os.walk(afs_base):
            level = root.replace(afs_base, '').count(os.sep)
            if level > 3:  # Limit depth
                continue
            indent = '  ' * level
            logger.info(f"{indent}{os.path.basename(root)}/")
            subindent = '  ' * (level + 1)
            for file in files[:10]:  # Limit files shown
                file_path = os.path.join(root, file)
                try:
                    size = os.path.getsize(file_path)
                    total_files += 1
                    total_size += size
                    logger.info(f"{subindent}{file} ({size} bytes)")
                except:
                    logger.info(f"{subindent}{file}")
            if len(files) > 10:
                logger.info(f"{subindent}... and {len(files) - 10} more files")
        
        logger.info("=== END AFS CONTENTS ===")
        logger.info(f"Total files in AFS: {total_files}, Total size: {total_size} bytes")
        
        # Check specific directories
        important_dirs = [
            AFS_PREDICTIONS_DIR,
            AFS_CACHE_DIR,
            AFS_FORECASTING_DIR,
            AFS_SCRAPED_DATA_DIR,
        ]
        
        for dir_path in important_dirs:
            if os.path.exists(dir_path):
                try:
                    file_count = len(os.listdir(dir_path))
                    logger.info(f"✅ {dir_path}: {file_count} items")
                except Exception as e:
                    logger.warning(f"⚠️  {dir_path}: exists but cannot list contents ({e})")
            else:
                logger.info(f"❌ {dir_path}: does not exist")
        
        return True
                
    except Exception as e:
        logger.error(f"Error reading AFS contents: {e}")
        return False


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
        
        # Debug AFS first
        debug_afs_only()
        
        # Verify AFS is available before proceeding
        if not os.path.exists(AFS_BASE):
            logger.error(f"Azure File Share not available at {AFS_BASE}. Cannot proceed.")
            logger.error("Please ensure Azure File Share is properly mounted.")
            sys.exit(1)
        
        # Test AFS write permissions
        try:
            test_file = os.path.join(AFS_BASE, "pipeline_test_write.tmp")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            logger.info("✅ AFS write permissions verified")
        except Exception as e:
            logger.error(f"❌ AFS write permission test failed: {e}")
            logger.error("Pipeline may fail due to insufficient AFS permissions")
        
        logger.info("Starting financial data processing pipeline using Azure File Share")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Working directory: {os.getcwd()}")
        logger.info(f"Arguments: {args}")
        logger.info(f"Azure File Share base: {AFS_BASE}")
        
        # Log AFS directory structure for debugging
        logger.info("=== AFS DIRECTORY STRUCTURE ===")
        for afs_dir in [AFS_PREDICTIONS_DIR, AFS_CACHE_DIR, AFS_FORECASTING_DIR, AFS_SCRAPED_DATA_DIR]:
            if os.path.exists(afs_dir):
                item_count = len(os.listdir(afs_dir))
                logger.info(f"  ✅ {afs_dir}: {item_count} items")
            else:
                logger.info(f"  ❌ {afs_dir}: does not exist (will be created)")
        logger.info("=== END AFS STRUCTURE ===")
        
        # Check required environment variables
        required_env_vars = ["FRED_API_KEY"]
        # Make AZURE_STORAGE_CONNECTION_STRING optional for local development
        optional_env_vars = ["AZURE_STORAGE_CONNECTION_STRING"]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        missing_optional = []
        for var in optional_env_vars:
            if not os.getenv(var):
                missing_optional.append(var)
        
        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            sys.exit(1)
        
        if missing_optional:
            logger.warning(f"Missing optional environment variables: {missing_optional}")
            logger.warning("Some features (like blob upload) may not work")
        
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
            # Check if we have Azure storage connection string
            if os.getenv("AZURE_STORAGE_CONNECTION_STRING"):
                logger.info("Starting upload step...")
                blob_url = upload_results_to_blob(args.container_name)
                if blob_url:
                    logger.info(f"Prediction results available at: {blob_url}")
                else:
                    logger.warning("Failed to upload results to Azure Blob Storage")
                    pipeline_success = False
            else:
                logger.warning("AZURE_STORAGE_CONNECTION_STRING not set - skipping blob upload")
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
        
        # Debug directory contents
        print("=== DIRECTORY CONTENTS DEBUG ===")
        try:
            import os
            for root, dirs, files in os.walk("/app"):
                level = root.replace("/app", "").count(os.sep)
                indent = " " * 2 * level
                print(f"{indent}{os.path.basename(root)}/")
                subindent = " " * 2 * (level + 1)
                for file in files[:5]:  # Limit to first 5 files per directory
                    print(f"{subindent}{file}")
                if len(files) > 5:
                    print(f"{subindent}... and {len(files) - 5} more files")
                if level > 3:  # Limit depth
                    break
        except Exception as e:
            print(f"Directory listing failed: {e}")
        print("=== END DIRECTORY DEBUG ===")
        
        # Check Azure File Share
        print("=== AZURE FILE SHARE DEBUG ===")
        try:
            if os.path.exists("/mnt/fileshare"):
                print("✅ Azure File Share mounted successfully")
                for root, dirs, files in os.walk("/mnt/fileshare"):
                    level = root.replace("/mnt/fileshare", "").count(os.sep)
                    if level <= 2:  # Limit depth
                        indent = " " * 2 * level
                        print(f"{indent}{os.path.basename(root)}/")
                        subindent = " " * 2 * (level + 1)
                        for file in files[:10]:  # Show up to 10 files
                            print(f"{subindent}{file}")
                        if len(files) > 10:
                            print(f"{subindent}... and {len(files) - 10} more files")
            else:
                print("❌ Azure File Share not mounted at /mnt/fileshare")
        except Exception as e:
            print(f"File share listing failed: {e}")
        print("=== END FILE SHARE DEBUG ===")
        
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
