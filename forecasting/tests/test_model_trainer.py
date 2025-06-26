"""
Unit tests for the model trainer module.
"""

import os
import unittest
from unittest.mock import patch, MagicMock, mock_open
import pandas as pd
import numpy as np
import json
import sys

# Add the parent directory to the path so we can import the module under test
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.modeling.model_trainer import ModelTrainer


class TestModelTrainer(unittest.TestCase):
    """Test cases for the ModelTrainer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.trainer = ModelTrainer(
            data_dir='test_data',
            output_dir='test_output',
            random_state=42
        )
    
    def test_initialize_models(self):
        """Test model initialization."""
        models = self.trainer._initialize_models()
        
        # Verify models were created
        self.assertEqual(len(models), 10, "Should initialize 10 different models")
        self.assertIn("Random Forest", models, "Random Forest model should be initialized")
        self.assertIn("Gradient Boosting", models, "Gradient Boosting model should be initialized")
        self.assertIn("Linear Regression", models, "Linear Regression model should be initialized")
    
    @patch('src.modeling.model_trainer.find_latest_file')
    @patch('pandas.read_csv')
    def test_load_data(self, mock_read_csv, mock_find_latest):
        """Test data loading and preparation."""
        # Configure mocks
        mock_find_latest.return_value = 'test_data/combined_data.csv'
        
        # Create a mock DataFrame with some test data
        mock_df = pd.DataFrame({
            'Date': ['2025-01-01', '2025-01-02', '2025-01-03'],
            'ticker': ['AAPL', 'MSFT', 'GOOGL'],
            'feature1': [1.0, 2.0, 3.0],
            'feature2': [0.1, 0.2, 0.3],
            'actual': [100.0, 200.0, np.NaN]
        })
        mock_read_csv.return_value = mock_df
        
        # Call the method
        train_df, test_df = self.trainer._load_data()
        
        # Verify results
        self.assertEqual(len(train_df), 2, "Training data should have 2 rows")
        self.assertEqual(len(test_df), 1, "Test data should have 1 row")
        self.assertEqual(test_df.iloc[0]['ticker'], 'GOOGL', "Test data should contain GOOGL")
        
        # Verify Date column was dropped
        self.assertNotIn('Date', train_df.columns, "Date column should be dropped from train data")
        
        # Verify mocks were called correctly
        mock_find_latest.assert_called_once_with('test_data', 'combined_data_until_*.csv')
        mock_read_csv.assert_called_once_with('test_data/combined_data.csv')
    
    def test_preprocess_data(self):
        """Test data preprocessing."""
        # Create test data
        df = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT', 'GOOGL'],
            'feature1': [1.0, 2.0, 3.0],
            'feature2': [0.1, 0.2, 0.3],
            'actual': [100.0, 200.0, 300.0]
        })
        
        # Call the method
        X_processed, y, categorical_cols, numerical_cols = self.trainer._preprocess_data(df)
        
        # Verify results
        self.assertEqual(X_processed.shape[0], 3, "Should have 3 processed rows")
        self.assertEqual(len(y), 3, "Target vector should have 3 values")
        self.assertEqual(categorical_cols, ['ticker'], "Should identify 'ticker' as categorical")
        self.assertEqual(set(numerical_cols), set(['feature1', 'feature2']), 
                       "Should identify numerical features correctly")
        
        # Encoder and scaler should have been fitted
        self.assertIsNotNone(self.trainer.encoder, "Encoder should be fitted")
        self.assertIsNotNone(self.trainer.scaler, "Scaler should be fitted")
    
    @patch('src.modeling.model_trainer.ModelTrainer._initialize_models')
    @patch('sklearn.model_selection.cross_val_score')
    def test_evaluate_models(self, mock_cross_val, mock_init_models):
        """Test model evaluation."""
        # Configure mocks
        mock_models = {
            'Model1': MagicMock(),
            'Model2': MagicMock()
        }
        mock_init_models.return_value = mock_models
        
        # Mock cross_val_score to return different values for different models
        mock_cross_val.side_effect = [
            np.array([-0.1, -0.2, -0.15, -0.12, -0.18]),  # Model1 MAE
            np.array([0.85, 0.82, 0.88, 0.84, 0.86]),     # Model1 R2
            np.array([-0.2, -0.3, -0.25, -0.22, -0.28]),  # Model2 MAE
            np.array([0.75, 0.72, 0.78, 0.74, 0.76])      # Model2 R2
        ]
        
        # Create test data
        X = np.array([[1, 2], [3, 4], [5, 6]])
        y = np.array([10, 20, 30])
        
        # Call the method
        results = self.trainer._evaluate_models(X, y)
        
        # Verify results
        self.assertEqual(len(results), 2, "Should evaluate 2 models")
        self.assertIn('model', results.columns, "Results should include model name")
        self.assertIn('mean_mae', results.columns, "Results should include MAE metric")
        self.assertIn('mean_r2', results.columns, "Results should include R² metric")
        
        # Model1 should have better MAE
        model1_row = results[results['model'] == 'Model1'].iloc[0]
        self.assertLess(model1_row['mean_mae'], 0.2, "Model1 should have MAE < 0.2")
        
        # Verify cross_val_score was called correctly
        self.assertEqual(mock_cross_val.call_count, 4, "cross_val_score should be called 4 times")
    
    @patch('os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    @patch('src.modeling.model_trainer.clean_old_files')
    @patch('src.modeling.model_trainer.get_next_friday')
    def test_save_predictions(self, mock_next_friday, mock_clean, mock_json_dump, 
                             mock_open_file, mock_makedirs):
        """Test saving predictions to JSON."""
        # Configure mocks
        mock_next_friday.return_value = '20250704'
        
        # Create test data
        test_df = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT', 'GOOGL'],
            'prediction': [150.5, 250.75, 1800.25]
        })
        
        # Call the method
        result = self.trainer._save_predictions(test_df)
        
        # Verify results
        expected_path = os.path.join('test_output', 'next_friday_predictions_20250704.json')
        self.assertEqual(result, expected_path, "Should return the correct output path")
        
        # Verify mocks were called correctly
        mock_clean.assert_called_once()
        mock_makedirs.assert_called_once_with('test_output', exist_ok=True)
        mock_open_file.assert_called_once_with(expected_path, 'w')
        
        # Verify JSON was written with the correct data
        expected_dict = {'AAPL': 150.5, 'MSFT': 250.75, 'GOOGL': 1800.25}
        mock_json_dump.assert_called_once()
        args, _ = mock_json_dump.call_args
        self.assertEqual(args[0], expected_dict, "Should write the correct predictions dict")

if __name__ == '__main__':
    unittest.main()
