"""
File system utilities for managing scraper data directories and files.
"""
import os
import shutil
from datetime import datetime
from typing import List, Optional, Tuple
from pathlib import Path
import pandas as pd

from constants import OUTPUT_DIR, FOLDER_DATE_FORMAT, OVERWRITE_CHOICE_MAP
from core.logger import ScraperLogger


class FileManager:
    """Handles file system operations for scraper data."""
    
    def __init__(self):
        self.logger = ScraperLogger.get_logger(self.__class__.__name__)
    
    def create_directory(self, directory_path: str) -> None:
        """Create directory if it doesn't exist.
        
        Args:
            directory_path: Full path to the directory to create
        """
        Path(directory_path).mkdir(parents=True, exist_ok=True)
        self.logger.debug(f"Ensured directory exists: {directory_path}")
    
    def find_folders_with_prefix(self, prefix: str) -> List[str]:
        """Find all folders in OUTPUT_DIR that start with the given prefix.
        
        Args:
            prefix: Folder name prefix to search for
            
        Returns:
            List of full paths to matching folders
        """
        if not os.path.exists(OUTPUT_DIR):
            return []
        
        matching_folders = []
        for folder in os.listdir(OUTPUT_DIR):
            if folder.startswith(prefix):
                matching_folders.append(os.path.join(OUTPUT_DIR, folder))
        
        return matching_folders
    
    def get_latest_folder(self, folder_paths: List[str]) -> Optional[str]:
        """Find the folder with the latest end date from folder paths.
        
        Args:
            folder_paths: List of folder paths to examine
            
        Returns:
            Path to the folder with the latest end date, or None if none found
        """
        latest_folder = None
        latest_date = None
        
        for folder_path in folder_paths:
            folder_name = os.path.basename(folder_path)
            try:
                # Extract end date from folder name (format: prefix_YYYYMMDD_YYYYMMDD)
                parts = folder_name.split('_')
                if len(parts) < 3:
                    continue
                    
                end_date_str = parts[-1]
                end_date = datetime.strptime(end_date_str, FOLDER_DATE_FORMAT)
                
                if latest_date is None or end_date > latest_date:
                    latest_date = end_date
                    latest_folder = folder_path
                    
            except (IndexError, ValueError) as e:
                self.logger.warning(f"Could not parse date from folder: {folder_name}, error: {e}")
                continue
        
        return latest_folder
    
    def create_data_folder(self, prefix: str, start_date: datetime, end_date: datetime) -> str:
        """Create a data folder with standardized naming.
        
        Args:
            prefix: Folder name prefix (e.g., ticker symbol or 'market_data')
            start_date: Start date of the data
            end_date: End date of the data
            
        Returns:
            Full path to the created folder
        """
        start_str = start_date.strftime(FOLDER_DATE_FORMAT)
        end_str = end_date.strftime(FOLDER_DATE_FORMAT)
        folder_name = f"{prefix}_{start_str}_{end_str}"
        folder_path = os.path.join(OUTPUT_DIR, folder_name)
        
        self.create_directory(folder_path)
        return folder_path
    
    def remove_folder(self, folder_path: str) -> bool:
        """Safely remove a folder and its contents.
        
        Args:
            folder_path: Path to the folder to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            shutil.rmtree(folder_path)
            folder_name = os.path.basename(folder_path)
            self.logger.info(f"Successfully removed folder: {folder_name}")
            return True
        except OSError as e:
            folder_name = os.path.basename(folder_path)
            self.logger.error(f"Error removing folder {folder_name}: {e}")
            return False
    
    def handle_user_choice(self, existing_folders: List[str]) -> str:
        """Handle user choice for existing data folders.
        
        Args:
            existing_folders: List of existing folder paths
            
        Returns:
            User's choice ('overwrite', 'update', or 'skip')
        """
        if not existing_folders:
            return 'overwrite'
        
        print("\nFound existing data folders:")
        for folder in existing_folders:
            print(f"- {os.path.basename(folder)}")
        
        print("\nOptions:")
        print("a) Overwrite all existing data")
        print("b) Update the most recent data")
        print("c) Skip")
        
        while True:
            choice = input("\nEnter your choice (a/b/c): ").lower().strip()
            if choice in OVERWRITE_CHOICE_MAP:
                return OVERWRITE_CHOICE_MAP[choice]
            else:
                self.logger.warning("Invalid choice. Please enter 'a', 'b', or 'c'.")
    
    def save_dataframe(self, df, file_path: str) -> bool:
        """Save DataFrame to CSV file.
        
        Args:
            df: DataFrame to save
            file_path: Full path where to save the file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            directory = os.path.dirname(file_path)
            self.create_directory(directory)
            
            # Save the DataFrame
            df.to_csv(file_path, index=False)
            self.logger.info(f"Saved data to: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving data to {file_path}: {e}")
            return False
    
    def load_dataframe(self, file_path: str, parse_dates: Optional[List[str]] = None) -> Optional[pd.DataFrame]:
        """Load DataFrame from CSV file.
        
        Args:
            file_path: Full path to the CSV file
            parse_dates: List of columns to parse as dates
            
        Returns:
            DataFrame if successful, None otherwise
        """
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"File not found: {file_path}")
                return None
            
            parse_dates = parse_dates or ['Date']
            df = pd.read_csv(file_path, parse_dates=parse_dates)
            self.logger.debug(f"Loaded data from: {file_path}")
            return df
        except Exception as e:
            self.logger.error(f"Error loading data from {file_path}: {e}")
            return None
