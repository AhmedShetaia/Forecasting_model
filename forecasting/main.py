"""
Main entry point for the forecasting application.

This script orchestrates the data preparation and model training processes.
"""

import os
import logging
import argparse
import pandas as pd
from typing import Dict, Any, Optional, Tuple

from src.config.constants import (
    DEFAULT_DATA_DIR, DEFAULT_INPUT_DIR, DEFAULT_LOG_LEVEL,
    LOG_FORMAT, DATE_FORMAT
)
from src.data_preparation.data_processor import DataProcessor
from src.modeling.model_trainer import ModelTrainer

# Configure logger
logger = logging.getLogger(__name__)

def configure_logging(level: str = DEFAULT_LOG_LEVEL) -> None:
    """
    Configure logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, level),
        format=LOG_FORMAT,
        handlers=[logging.StreamHandler()]
    )

def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Run the forecasting pipeline: data preparation and model training."
    )
    parser.add_argument(
        '--log-level', 
        dest='loglevel', 
        default=DEFAULT_LOG_LEVEL,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help=f'Set the logging level (default: {DEFAULT_LOG_LEVEL})'
    )
    parser.add_argument(
        '--skip-data-prep',
        dest='skip_data_prep',
        action='store_true',
        help='Skip the data preparation step'
    )
    parser.add_argument(
        '--skip-training',
        dest='skip_training',
        action='store_true',
        help='Skip the model training step'
    )
    parser.add_argument(
        '--data-dir',
        dest='data_dir',
        default=DEFAULT_DATA_DIR,
        help=f'Directory for input/output data files (default: {DEFAULT_DATA_DIR})'
    )
    
    parser.add_argument(
        '--input-dir',
        dest='input_dir',
        default=None,
        help=f'Optional: Specific input directory (if different from data-dir, default: {DEFAULT_INPUT_DIR})'
    )
    return parser.parse_args()

def run_data_preparation(input_dir: str, output_dir: str, data_dir: str) -> str:
    """
    Run the data preparation process.
    
    Args:
        input_dir: Directory containing input data
        output_dir: Directory to save prediction output files
        data_dir: Parent data directory where combined data will be saved
        
    Returns:
        Path to the prepared data file
    """
    
    # Ensure directories exist
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    
    # Create data processor and prepare data with data_dir as output path
    processor = DataProcessor(
        predictions_dir=None,  # Use default
        market_data_dir=None,  # Use default
        output_path=data_dir  # Save combined data to parent data dir
    )
    combined_data = processor.prepare_data(save_output=True)
    
    # Get the output path
    dates = combined_data['Date'].sort_values().unique()
    if len(dates) >= 2:
        second_latest_date = pd.to_datetime(dates[-2]).strftime(DATE_FORMAT)
    else:
        second_latest_date = pd.to_datetime(dates[-1]).strftime(DATE_FORMAT)
    
    output_path = os.path.join(data_dir, f"combined_data_until_{second_latest_date}.csv")
    
    return output_path

def run_model_training(input_dir: str, output_dir: str, data_dir: str) -> tuple[str, str]:
    """
    Run the model training process.
    
    Args:
        input_dir: Directory containing input data files
        output_dir: Directory to save prediction output files
        data_dir: Parent data directory where predictions will be saved
        
    Returns:
        Tuple containing:
            - Path to the predictions file
            - Name of the best model (for reference, logging handled in ModelTrainer)
    """
    # Create model trainer and generate predictions
    # The combined_data is read from data_dir and predictions are saved to data_dir
    trainer = ModelTrainer(data_dir=data_dir, output_dir=data_dir)
    predictions_path, predictions = trainer.train_and_predict()
    
    # Return both the path and the best model name which is available in the trainer object
    return predictions_path, trainer.best_model_name

def main() -> None:
    """
    Main entry point for the forecasting pipeline.
    """
    # Parse command-line arguments
    args = parse_args()
    
    # Configure logging
    configure_logging(args.loglevel)
    
    logger.info("Starting forecasting pipeline...")
    
    # Normalize and standardize directory paths
    data_dir = os.path.abspath(args.data_dir)
    # If data_dir points to input dir, get its parent to use as data_dir
    if data_dir.endswith('input'):
        data_dir = os.path.dirname(data_dir)
    
    input_dir = os.path.join(data_dir, 'input')
    output_dir = os.path.join(data_dir, 'output')
    
    if args.input_dir:
        input_dir = os.path.abspath(args.input_dir)
    
    # Ensure directories exist
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"Using data directory: {data_dir}")
    logger.info(f"Using input directory: {input_dir}")
    logger.info(f"Using output directory: {output_dir}")
    
    # Run data preparation if not skipped
    if not args.skip_data_prep:
        # Combined data is saved to data_dir to be used for model training
        data_path = run_data_preparation(input_dir=input_dir, output_dir=output_dir, data_dir=data_dir)
        logger.info(f"Data preparation complete, combined data saved to: {data_path}")
    else:
        logger.info("Skipping data preparation step...")
    
    # Run model training if not skipped
    if not args.skip_training:
        # Combined data file from data_dir is used as input, and predictions are saved to data_dir
        predictions_path, best_model = run_model_training(input_dir=input_dir, output_dir=output_dir, data_dir=data_dir)
    else:
        logger.info("Skipping model training step...")
    
    logger.info("Forecasting pipeline completed successfully!")

if __name__ == "__main__":
    main()
