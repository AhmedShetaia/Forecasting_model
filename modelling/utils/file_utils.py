"""File utilities for saving and loading predictions."""
import os
import pandas as pd
import logging
from datetime import datetime
from pathlib import Path
from ..config.constants import PREDICTIONS_DIR, DATE_FORMAT, TIMESTAMP_FORMAT

logger = logging.getLogger(__name__)


def find_company_folder(scraped_folder, ticker):
    """Find the folder containing data for a specific company.
    
    Args:
        scraped_folder: Path to folder containing scraped data
        ticker: Company ticker symbol
        
    Returns:
        Path to the company data folder, or None if not found
    """
    scraped_folder = Path(scraped_folder)
    
    # Look for folders with the ticker prefix
    for item in scraped_folder.glob(f"{ticker}_*"):
        if item.is_dir():
            return item
            
    logger.warning(f"No data folder found for ticker {ticker}")
    return None


def save_predictions(predictions_df, base_path=None, ticker=None, start_date=None, end_date=None):
    """Save predictions to CSV file.
    
    Args:
        predictions_df: DataFrame containing predictions
        base_path: Base path for output file (without extension)
        ticker: Company ticker symbol
        start_date: Start date of data
        end_date: End date of data
        
    Returns:
        Path to the saved CSV file
    """
    # Ensure output directory exists
    output_dir = os.path.dirname(base_path) if base_path else PREDICTIONS_DIR
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamp for filename
    timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
    
    # Build filename components
    filename_parts = ["model_predictions", timestamp]
    
    # Add ticker if provided
    if ticker:
        filename_parts.append(ticker)
    
    # Add date range if provided
    if start_date and end_date:
        start_str = start_date.strftime(DATE_FORMAT) if isinstance(start_date, datetime) else start_date
        end_str = end_date.strftime(DATE_FORMAT) if isinstance(end_date, datetime) else end_date
        filename_parts.extend([start_str, end_str])
    
    # Build final path
    filename = "_".join(filename_parts) + ".csv"
    
    if base_path:
        # If base path provided, use it as directory
        output_path = os.path.join(os.path.dirname(base_path), filename)
    else:
        # Otherwise use the default predictions directory
        output_path = os.path.join(PREDICTIONS_DIR, filename)
    
    # Remove any existing error columns
    error_cols = [col for col in predictions_df.columns if col.endswith('_error')]
    if error_cols:
        predictions_df = predictions_df.drop(columns=error_cols)
    
    # Save the file
    predictions_df.to_csv(output_path, index=False)
    logger.info(f"Predictions saved to {output_path}")
    
    return output_path
