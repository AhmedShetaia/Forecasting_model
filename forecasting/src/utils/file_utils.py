"""
File utility functions for the forecasting model.
"""

import os
import glob
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union

from ..config.constants import DATE_FORMAT

logger = logging.getLogger(__name__)

def find_latest_file(directory: str, pattern: str) -> str:
    """
    Find the latest file in a directory matching a given pattern.
    
    Args:
        directory: The directory to search in
        pattern: The glob pattern to match files
        
    Returns:
        The path to the latest file matching the pattern
        
    Raises:
        FileNotFoundError: If no matching files are found
    """
    file_pattern = os.path.join(directory, pattern)
    matching_files = glob.glob(file_pattern)
    
    if not matching_files:
        logger.error(f"No files matching {pattern} found in {directory}")
        raise FileNotFoundError(f"No files matching {pattern} found in {directory}")
    
    # Sort files by the number in the filename (descending)
    matching_files.sort(key=lambda x: int(os.path.splitext(os.path.basename(x))[0].split('_')[-1]), 
                      reverse=True)
    
    latest_file = matching_files[0]
    logger.debug(f"Latest file found: {latest_file}")
    return latest_file

def get_file_path(base_path: str, relative_path: str) -> str:
    """
    Get an absolute file path, first trying with absolute path,
    then falling back to relative path.
    
    Args:
        base_path: Base directory to join with relative path
        relative_path: Relative path to the file
        
    Returns:
        The absolute path to the file
        
    Raises:
        FileNotFoundError: If the file is not found at either location
    """
    abs_path = os.path.abspath(os.path.join(os.path.dirname(base_path), relative_path))
    
    if os.path.exists(abs_path):
        return abs_path
        
    if os.path.exists(relative_path):
        return relative_path
        
    logger.error(f"File not found at: {abs_path} or {relative_path}")
    raise FileNotFoundError(f"File not found at: {abs_path} or {relative_path}")

def get_next_friday() -> str:
    """
    Calculate the date of the next Friday.
    
    Returns:
        The date of the next Friday in YYYYMMDD format
    """
    today = datetime.now()
    days_ahead = 4 - today.weekday()  # 4 = Friday
    
    if days_ahead <= 0:
        days_ahead += 7
        
    next_friday = today + timedelta(days=days_ahead)
    return next_friday.strftime(DATE_FORMAT)

def clean_old_files(directory: str, pattern: str) -> None:
    """
    Remove old files matching a given pattern from a directory.
    
    Args:
        directory: The directory containing the files
        pattern: The glob pattern to match files to be removed
    """
    for file_path in glob.glob(os.path.join(directory, pattern)):
        try:
            os.remove(file_path)
            logger.info(f"Deleted old file: {file_path}")
        except Exception as e:
            logger.warning(f"Could not delete file {file_path}: {e}")
