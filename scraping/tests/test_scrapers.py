"""
Example unit tests for the refactored scraping system.
Run with: python -m pytest tests/
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime

from scrapers.company_scraper import CompanyScraper
from core.data_processor import DataProcessor
from core.file_manager import FileManager


class TestCompanyScraper(unittest.TestCase):
    """Test cases for CompanyScraper."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.scraper = CompanyScraper("AAPL")
    
    def test_ticker_normalization(self):
        """Test that ticker symbols are normalized to uppercase."""
        scraper = CompanyScraper("aapl")
        self.assertEqual(scraper.ticker, "AAPL")
    
    def test_folder_prefix(self):
        """Test folder prefix generation."""
        self.assertEqual(self.scraper._get_folder_prefix(), "AAPL_")
    
    def test_filename_generation(self):
        """Test filename generation."""
        self.assertEqual(self.scraper._get_filename(), "AAPL_data.csv")
    
    @patch('yfinance.Ticker')
    def test_fetch_raw_data_success(self, mock_ticker):
        """Test successful data fetching."""
        # Mock yfinance response
        mock_stock = Mock()
        mock_data = pd.DataFrame({
            'Close': [100, 101, 102],
            'Volume': [1000, 1100, 1200]
        }, index=pd.date_range('2023-01-01', periods=3))
        
        mock_stock.history.return_value = mock_data
        mock_ticker.return_value = mock_stock
        
        result = self.scraper._fetch_raw_data("2023-01-01")
        
        self.assertFalse(result.empty)
        mock_ticker.assert_called_once_with("AAPL")
        mock_stock.history.assert_called_once()
    
    @patch('yfinance.Ticker')
    def test_fetch_raw_data_empty(self, mock_ticker):
        """Test handling of empty data response."""
        mock_stock = Mock()
        mock_stock.history.return_value = pd.DataFrame()
        mock_ticker.return_value = mock_stock
        
        result = self.scraper._fetch_raw_data("2023-01-01")
        
        self.assertTrue(result.empty)


class TestDataProcessor(unittest.TestCase):
    """Test cases for DataProcessor."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = DataProcessor()
    
    def test_normalize_timezone(self):
        """Test timezone normalization."""
        # Create DataFrame with timezone-aware index
        index = pd.date_range('2023-01-01', periods=3, tz='UTC')
        df = pd.DataFrame({'value': [1, 2, 3]}, index=index)
        
        result = self.processor.normalize_timezone(df)
        
        self.assertIsNone(result.index.tz)
    
    def test_resample_to_weekly(self):
        """Test weekly resampling."""
        # Create daily data
        index = pd.date_range('2023-01-01', periods=7)
        df = pd.DataFrame({'Close': range(7)}, index=index)
        
        result = self.processor.resample_to_weekly(df)
        
        self.assertIn('Date', result.columns)
        self.assertIn('Weekly_Close', result.columns)
        self.assertEqual(len(result), 1)  # Should have one week
    
    def test_normalize_dates(self):
        """Test date normalization and duplicate removal."""
        df = pd.DataFrame({
            'Date': ['2023-01-01', '2023-01-01', '2023-01-02'],
            'value': [1, 2, 3]
        })
        
        result = self.processor.normalize_dates(df)
        
        # Should remove duplicate dates, keeping the last one
        self.assertEqual(len(result), 2)
        self.assertEqual(result.iloc[0]['value'], 2)  # Last value for 2023-01-01


class TestFileManager(unittest.TestCase):
    """Test cases for FileManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.file_manager = FileManager()
    
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_find_folders_with_prefix(self, mock_listdir, mock_exists):
        """Test finding folders with prefix."""
        mock_exists.return_value = True
        mock_listdir.return_value = ['AAPL_20230101_20231231', 'MSFT_20230101_20231231', 'other_folder']
        
        result = self.file_manager.find_folders_with_prefix('AAPL_')
        
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].endswith('AAPL_20230101_20231231'))
    
    def test_get_latest_folder(self):
        """Test getting the latest folder by date."""
        folders = [
            'output/AAPL_20230101_20230630',
            'output/AAPL_20230101_20231231'
        ]
        
        result = self.file_manager.get_latest_folder(folders)
        
        self.assertEqual(result, 'output/AAPL_20230101_20231231')
    
    def test_create_data_folder(self):
        """Test data folder creation with proper naming."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        with patch.object(self.file_manager, 'create_directory') as mock_create:
            result = self.file_manager.create_data_folder('AAPL', start_date, end_date)
            
            self.assertTrue(result.endswith('AAPL_20230101_20231231'))
            mock_create.assert_called_once()


if __name__ == '__main__':
    unittest.main()
