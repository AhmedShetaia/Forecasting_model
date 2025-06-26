"""SARIMA time series forecasting model implementation."""
import os
import json
import logging
import warnings
import pandas as pd
import pmdarima as pm
from .base_model import BaseTimeSeriesModel
from ..config.constants import SARIMA_CACHE_DIR

# Suppress statsmodels and pmdarima warnings
warnings.filterwarnings('ignore')


class SARIMAPredictor(BaseTimeSeriesModel):
    """SARIMA model for time series forecasting."""
    
    def __init__(self, cache_dir=None, log_level=logging.INFO):
        """Initialize the SARIMA model.
        
        Args:
            cache_dir: Directory to cache model parameters
            log_level: Logging level
        """
        super().__init__(log_level)
        self.model = None
        self.order = None
        self.seasonal_order = None
        self.cache_dir = cache_dir or SARIMA_CACHE_DIR
        
        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_params_filepath(self, ticker):
        """Get the path to the cached parameters file for a ticker.
        
        Args:
            ticker: Company ticker symbol
            
        Returns:
            Path to cached parameters file
        """
        return os.path.join(self.cache_dir, f"{ticker}_params.json")
    
    def train(self, data, ticker=None, force_retrain=False):
        """Train the SARIMA model.
        
        Args:
            data: DataFrame with Date and Weekly_Close columns or a Series
            ticker: Company ticker symbol for parameter caching
            force_retrain: Whether to force retraining even if cached parameters exist
            
        Returns:
            None
        """
        data = self._validate_data(data) if isinstance(data, pd.DataFrame) else data
        
        # Extract time series
        series = data['Weekly_Close'] if isinstance(data, pd.DataFrame) else data
        
        # If ticker is provided, try to use cached parameters
        if ticker and not force_retrain:
            params_filepath = self._get_params_filepath(ticker)
            
            if os.path.exists(params_filepath):
                self.logger.info(f"Loading cached SARIMA parameters for {ticker}")
                with open(params_filepath, 'r') as f:
                    params = json.load(f)
                    
                self.order = tuple(params['order'])
                self.seasonal_order = tuple(params['seasonal_order'])
                
                self.logger.info(f"Using cached parameters: {self.order}, {self.seasonal_order}")
                self.model = pm.ARIMA(order=self.order, seasonal_order=self.seasonal_order).fit(series)
                return
        
        # No cache or forced retraining - run auto_arima
        self.logger.info("Running auto_arima parameter search...")
        self.model = pm.auto_arima(
            series,
            start_p=1, start_q=1,
            test='adf',
            max_p=3, max_q=3,
            m=52,  # Weekly seasonality
            d=None,  # Let the model determine differencing
            seasonal=True,
            start_P=0,
            D=1,  # Seasonal differencing
            trace=self.logger.level == logging.DEBUG,
            error_action='ignore',
            suppress_warnings=True,
            stepwise=True
        )
        
        self.order = self.model.order
        self.seasonal_order = self.model.seasonal_order
        
        # Save parameters if ticker is provided
        if ticker:
            params_filepath = self._get_params_filepath(ticker)
            self.logger.info(f"Saving optimal parameters for {ticker} to cache")
            
            params_to_save = {
                'order': self.order,
                'seasonal_order': self.seasonal_order
            }
            
            with open(params_filepath, 'w') as f:
                json.dump(params_to_save, f)
                
        self.logger.info(f"Model trained with parameters: {self.order}, {self.seasonal_order}")
    
    def predict(self, steps=1, **kwargs):
        """Generate predictions using the trained SARIMA model.
        
        Args:
            steps: Number of steps to forecast
            
        Returns:
            Forecasted values
            
        Raises:
            ValueError: If model hasn't been trained
        """
        if self.model is None:
            raise ValueError("Model must be trained before making predictions")
            
        predictions = self.model.predict(n_periods=steps)
        return predictions.iloc[0] if steps == 1 else predictions
