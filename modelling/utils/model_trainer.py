"""Model trainer module for time series forecasting."""
import json
import logging
import pandas as pd
from tqdm import tqdm
import numpy as np
from datetime import timedelta

from ..models.sarima_model import SARIMAPredictor
from ..models.autots_model import AutoTSPredictor
from ..models.timemoe_model import TimeMOEPredictor
from ..config.constants import MODEL_CONFIG_PATH, TIMEMOE_CACHE_DIR


class ModelTrainer:
    """Class for training and evaluating time series forecasting models."""
    
    def __init__(self, config_path=None, cache_dir=None, log_level=logging.INFO):
        """Initialize model trainer.
        
        Args:
            config_path: Path to model configuration JSON file
            cache_dir: Directory to cache TimeMOE model
            log_level: Logging level
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        self.config_path = config_path or MODEL_CONFIG_PATH
        self.cache_dir = cache_dir or TIMEMOE_CACHE_DIR
        
        # Load configuration
        self._load_config()
        
        # Initialize models
        self.models = self._initialize_models(log_level)
    
    def _load_config(self):
        """Load model configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            self.logger.info(f"Loaded configuration from {self.config_path}")
        except Exception as e:
            self.logger.warning(f"Failed to load config from {self.config_path}: {e}")
            self.logger.warning("Using default configuration")
            self.config = {"test_size": 0.2}
    
    def _initialize_models(self, log_level):
        """Initialize forecasting models.
        
        Args:
            log_level: Logging level for models
            
        Returns:
            Dictionary of model name to model instance
        """
        return {
            'SARIMA': SARIMAPredictor(log_level=log_level),
            'AutoTS': AutoTSPredictor(log_level=log_level),
            'TimeMOE': TimeMOEPredictor(cache_dir=self.cache_dir, log_level=log_level)
        }
    
    def train(self, train_data, test_data, ticker):
        """Train models and generate predictions using rolling window.
        
        Args:
            train_data: Training data DataFrame
            test_data: Test data DataFrame
            ticker: Company ticker symbol
            
        Returns:
            DataFrame with predictions from all models
        """
        results = []
        current_train = train_data.copy()
        
        for idx, row in tqdm(test_data.iterrows(), total=len(test_data), desc=f"Training models for {ticker}"):
            predictions = {'Date': row['Date'], 'ticker': ticker}
            
            # Get predictions from each model
            for name, model in self.models.items():
                try:
                    self.logger.info(f"Training {name} model (window {idx - train_data.index[0] + 1})")
                    
                    # Train model on current data
                    if name == 'SARIMA':
                        model.train(current_train, ticker=ticker)
                    else:
                        model.train(current_train)
                    
                    # Make prediction
                    self.logger.info(f"Predicting with {name} model")
                    pred = model.predict()
                    
                    # Handle different return types
                    if hasattr(pred, 'item'):
                        pred = pred.item()
                    
                    predictions[f'{name}_pred'] = pred
                    
                except Exception as e:
                    self.logger.error(f"Error in {name} model: {str(e)}")
                    predictions[f'{name}_pred'] = np.nan
            
            # Store actual value
            predictions['actual'] = row['Weekly_Close']
            results.append(predictions)
            
            # Update training data with the current observation
            current_train = pd.concat([
                current_train, 
                pd.DataFrame([row])
            ]).reset_index(drop=True)
        
        return pd.DataFrame(results)
    
    def forecast_next_week(self, data, ticker):
        """Generate forecast for next week using all available data.
        
        Args:
            data: Complete historical data
            ticker: Company ticker symbol
            
        Returns:
            Dictionary with next week forecast from all models
        """
        # Calculate next week's date
        next_week_date = data['Date'].max() + timedelta(days=7)
        next_week_row = {'Date': next_week_date, 'actual': None, 'ticker': ticker}

        # Get clean data for training (no missing values)
        clean_data = data.dropna(subset=['Weekly_Close'])
        
        for name, model in self.models.items():
            try:
                self.logger.info(f"Training {name} on full dataset for next-week forecast")
                
                if name == 'SARIMA':
                    model.train(clean_data, ticker=ticker)
                else:
                    model.train(clean_data)

                pred = model.predict()
                
                if hasattr(pred, 'item'):
                    pred = pred.item()
                    
                next_week_row[f'{name}_pred'] = pred
                
            except Exception as e:
                self.logger.error(f"Error forecasting with {name}: {str(e)}")
                next_week_row[f'{name}_pred'] = np.nan

        return next_week_row
