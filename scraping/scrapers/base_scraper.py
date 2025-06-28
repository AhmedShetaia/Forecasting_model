"""
Base scraper class with common functionality.
"""
import os
import pandas as pd
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional

from ..constants import DATE_COLUMN, DAYS_FOR_RECENT_CHECK
from ..core.logger import ScraperLogger
from ..core.file_manager import FileManager
from ..core.data_processor import DataProcessor


class BaseScraper(ABC):
    """Base class for all data scrapers."""
    
    def __init__(self, name: str):
        """Initialize base scraper.
        
        Args:
            name: Name identifier for the scraper
        """
        self.name = name
        self.logger = ScraperLogger.get_logger(f"{self.__class__.__name__}_{name}")
        self.file_manager = FileManager()
        self.data_processor = DataProcessor()
    
    @abstractmethod
    def _fetch_raw_data(self, start_date: str) -> pd.DataFrame:
        """Fetch raw data from the data source.
        
        Args:
            start_date: Start date for data fetching
            
        Returns:
            Raw DataFrame from the data source
        """
        pass
    
    @abstractmethod
    def _get_folder_prefix(self) -> str:
        """Get the folder prefix for this scraper's data.
        
        Returns:
            Folder prefix string
        """
        pass
    
    @abstractmethod
    def _get_filename(self) -> str:
        """Get the filename for saving data.
        
        Returns:
            Filename string
        """
        pass
    
    def _is_data_recent(self, last_date: datetime) -> bool:
        """Check if data is recent enough to skip updating.
        
        Args:
            last_date: Latest date in existing data
            
        Returns:
            True if data is recent enough
        """
        cutoff_date = datetime.now().date() - timedelta(days=DAYS_FOR_RECENT_CHECK)
        return last_date.date() >= cutoff_date
    
    def _process_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process raw data (can be overridden by subclasses).
        
        Args:
            df: Raw DataFrame
            
        Returns:
            Processed DataFrame
        """
        return df
    
    def _update_existing_data(self) -> bool:
        """Update existing data with new data.
        
        Returns:
            True if update was successful or not needed, False if failed
        """
        self.logger.info(f"Attempting to update data for {self.name}")
        
        # Find existing folders
        existing_folders = self.file_manager.find_folders_with_prefix(self._get_folder_prefix())
        if not existing_folders:
            self.logger.info(f"No existing data to update for {self.name}")
            return False
        
        # Get latest folder
        latest_folder_path = self.file_manager.get_latest_folder(existing_folders)
        if not latest_folder_path:
            self.logger.error("Could not determine latest folder")
            return False
        
        latest_folder_name = os.path.basename(latest_folder_path)
        self.logger.info(f"Found latest data in: {latest_folder_name}")
        
        # Load existing data
        old_data_path = os.path.join(latest_folder_path, self._get_filename())
        old_data = self.file_manager.load_dataframe(old_data_path)
        if old_data is None:
            self.logger.error(f"Could not load existing data from {latest_folder_name}")
            return False
        
        # Check if data is recent enough
        last_date = old_data[DATE_COLUMN].max()
        if self._is_data_recent(last_date):
            self.logger.info(f"Data for {self.name} is already recent. No update needed.")
            return True
        
        # Fetch new data
        new_start_date = (last_date + timedelta(days=1)).strftime('%Y-%m-%d')  
        new_data = self._fetch_raw_data(new_start_date)
        
        if new_data.empty:
            self.logger.info(f"No new data found for {self.name} since {last_date.date()}")
            return True
        
        # Process new data
        new_data = self._process_data(new_data)
        
        # Combine old and new data
        combined_data = pd.concat([old_data, new_data], ignore_index=True)
        combined_data = self.data_processor.normalize_dates(combined_data)
        
        # Create new folder and save
        start_date = combined_data[DATE_COLUMN].min()
        end_date = combined_data[DATE_COLUMN].max()
        
        new_folder_path = self.file_manager.create_data_folder(
            self._get_folder_prefix().rstrip('_'), start_date, end_date
        )
        
        # Check if folder name would be the same (no new data)
        new_folder_name = os.path.basename(new_folder_path)
        if latest_folder_name == new_folder_name:
            self.logger.info(f"Data for {self.name} is already up to date")
            return True
        
        # Save updated data
        file_path = os.path.join(new_folder_path, self._get_filename())
        success = self.file_manager.save_dataframe(combined_data, file_path)
        
        if success:
            # Remove old folder
            self.file_manager.remove_folder(latest_folder_path)
        
        return success
    
    def save_data(self, start_date: str, force: bool = False) -> bool:
        """Save data with user interaction for existing data.
        
        Args:
            start_date: Start date for data fetching
            force: If True, skip user interaction and overwrite
            
        Returns:
            True if successful, False otherwise
        """
        # Check for existing data
        existing_folders = self.file_manager.find_folders_with_prefix(self._get_folder_prefix())
        
        if existing_folders and not force:
            choice = self.file_manager.handle_user_choice(existing_folders)
            
            if choice == 'update':
                return self._update_existing_data()
            elif choice == 'skip':
                self.logger.info(f"Skipping data scraping for {self.name}")
                return True
            elif choice == 'overwrite':
                self.logger.info(f"Overwriting existing data for {self.name}")
                for folder_path in existing_folders:
                    self.file_manager.remove_folder(folder_path)        # Fetch and process new data
        try:
            raw_data = self._fetch_raw_data(start_date)
            if raw_data.empty:
                self.logger.error(f"No data found for {self.name}")
                return False
            
            processed_data = self._process_data(raw_data)
            
            # Create folder and save
            start_date_dt = processed_data[DATE_COLUMN].min()
            end_date_dt = processed_data[DATE_COLUMN].max()
            
            folder_path = self.file_manager.create_data_folder(
                self._get_folder_prefix().rstrip('_'), start_date_dt, end_date_dt
            )
            
            file_path = os.path.join(folder_path, self._get_filename())
            return self.file_manager.save_dataframe(processed_data, file_path)
            
        except Exception as e:
            self.logger.error(f"Error saving data for {self.name}: {e}")
            return False
