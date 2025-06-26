"""
Unit tests for the data processor module.
"""

import os
import unittest
from unittest.mock import patch, MagicMock, mock_open
import pandas as pd
import numpy as np
import sys
import io

# Add the parent directory to the path so we can import the module under test
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_preparation.data_processor import DataProcessor


class TestDataProcessor(unittest.TestCase):
    """Test cases for the DataProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.data_processor = DataProcessor()
    
    @patch('src.data_preparation.data_processor.get_file_path')
    @patch('src.data_preparation.data_processor.glob.glob')
    def test_find_prediction_files(self, mock_glob, mock_get_path):
        """Test finding prediction files."""
        # Configure mocks
        mock_get_path.return_value = '/mocked/path/to/predictions'
        mock_glob.return_value = [
            '/mocked/path/to/predictions/file1.csv', 
            '/mocked/path/to/predictions/file2.csv'
        ]
        
        # Call the method
        result = self.data_processor._find_prediction_files()
        
        # Verify the result
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], '/mocked/path/to/predictions/file1.csv')
        
        # Verify mocks were called correctly
        mock_get_path.assert_called_once()
        mock_glob.assert_called_once()
    
    @patch('src.data_preparation.data_processor.get_file_path')
    @patch('src.data_preparation.data_processor.glob.glob')
    @patch('src.data_preparation.data_processor.os.path.exists')
    @patch('pandas.read_csv')
    def test_load_market_data(self, mock_read_csv, mock_path_exists, mock_glob, mock_get_path):
        """Test loading market data."""
        # Configure mocks
        mock_get_path.return_value = '/mocked/path/to/scraped_data'
        mock_glob.return_value = [
            '/mocked/path/to/scraped_data/market_data_20200101_20250101',
            '/mocked/path/to/scraped_data/market_data_20200101_20250620'  # Latest
        ]
        mock_path_exists.return_value = True
        mock_df = pd.DataFrame({'Date': ['2025-01-01', '2025-01-02'], 'Value': [100, 200]})
        mock_read_csv.return_value = mock_df
        
        # Call the method
        result = self.data_processor._load_market_data()
        
        # Verify the result
        pd.testing.assert_frame_equal(result, mock_df)
        
        # Verify mocks were called correctly
        mock_get_path.assert_called_once()
        mock_glob.assert_called_once()
        mock_read_csv.assert_called_once_with('/mocked/path/to/scraped_data/market_data_20200101_20250620/market_data.csv')
    
    @patch('pandas.read_csv')
    def test_combine_predictions(self, mock_read_csv):
        """Test combining prediction files."""
        # Configure the mock for multiple calls
        mock_df1 = pd.DataFrame({'Date': ['2025-01-01'], 'Value': [100]})
        mock_df2 = pd.DataFrame({'Date': ['2025-01-02'], 'Value': [200]})
        mock_read_csv.side_effect = [mock_df1, mock_df2]
        
        # Call the method
        result = self.data_processor._combine_predictions([
            '/mocked/path/file1.csv', 
            '/mocked/path/file2.csv'
        ])
        
        # Verify the result
        self.assertEqual(len(result), 2)
        self.assertEqual(result.iloc[0]['Value'], 100)
        self.assertEqual(result.iloc[1]['Value'], 200)
        
        # Verify mock was called correctly
        self.assertEqual(mock_read_csv.call_count, 2)
    
    def test_merge_with_market_data(self):
        """Test merging predictions with market data."""
        # Create test dataframes
        predictions_df = pd.DataFrame({
            'Date': pd.to_datetime(['2025-01-08', '2025-01-15']),
            'ticker': ['AAPL', 'MSFT'],
            'prediction': [150, 250]
        })
        
        market_df = pd.DataFrame({
            'Date': pd.to_datetime(['2025-01-01', '2025-01-08']),
            'ticker': ['AAPL', 'MSFT'],
            'price': [100, 200]
        })
        
        # Call the method
        result = self.data_processor._merge_with_market_data(predictions_df, market_df)
        
        # Verify the result
        self.assertEqual(len(result), 2)
        self.assertIn('prediction', result.columns)
        self.assertIn('price', result.columns)
        
        # First row should match with the first market data row
        self.assertEqual(result.iloc[0]['prediction'], 150)
        self.assertEqual(result.iloc[0]['price'], 100)

if __name__ == '__main__':
    unittest.main()
