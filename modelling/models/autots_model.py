"""AutoTS time series forecasting model implementation."""
import logging
import pandas as pd
import numpy as np
import os
import sys
from autots import AutoTS
from .base_model import BaseTimeSeriesModel


class AutoTSPredictor(BaseTimeSeriesModel):
    """AutoTS model for time series forecasting."""
    
    def __init__(self, log_level=logging.INFO):
        """Initialize the AutoTS model.
        
        Args:
            log_level: Logging level
        """
        super().__init__(log_level)
        self.model = None
        self.forecast = None
        
    def train(self, data, **kwargs):
        """Train the AutoTS model.
        
        Args:
            data: DataFrame with Date and Weekly_Close columns
            
        Returns:
            None
        """
        data = self._validate_data(data)
        
        # Store original data for fallback predictions if needed
        self.data = data.copy()
        
        self.logger.info("Preparing data for AutoTS model...")
        
        try:
            # Create a copy to avoid modifying the original
            df = data.copy()
            
            # Ensure data is properly formatted
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values('Date')
            
            self.logger.info("Training AutoTS model...")
            
            # Initialize and train the model with reasonable defaults
            self.model = AutoTS(
                forecast_length=1,
                frequency='W',  # Weekly data
                ensemble=None,
                model_list="superfast",  # Using faster model set
                transformer_list="superfast",
                max_generations=4,
                num_validations=2,
                validation_method="backwards",
                verbose=0  # Suppress AutoTS's own prints
            )
            
            self.logger.info("Fitting AutoTS model...")
            
            # Suppress verbose output from AutoTS during fitting
            original_stdout = sys.stdout
            original_stderr = sys.stderr
            sys.stdout = open(os.devnull, 'w')
            sys.stderr = open(os.devnull, 'w')
            
            try:
                self.model = self.model.fit(
                    df,
                    date_col='Date',  # Use the Date column directly
                    value_col='Weekly_Close'
                )
            finally:
                sys.stdout.close()
                sys.stderr.close()
                sys.stdout = original_stdout
                sys.stderr = original_stderr
            self.logger.info("AutoTS model training complete")
        
        except Exception as e:
            self.logger.error(f"Error in AutoTS model training: {str(e)}")
            self.model = None
    
    def predict(self, steps=1, **kwargs):
        """Generate predictions using the trained AutoTS model.
        
        Args:
            steps: Number of steps to forecast (ignored, AutoTS uses forecast_length from init)
            
        Returns:
            Forecasted values
            
        Raises:
            ValueError: If model hasn't been trained
        """
        if self.model is None:
            raise ValueError("Model must be trained before making predictions")
            
        self.logger.info("Generating AutoTS forecast...")
        try:
            prediction = self.model.predict()
            
            # Get the point forecast (mean prediction)
            forecast_value = float(prediction.forecast.values[0][0])  # Ensure it's a float
            
            # Log prediction details
            self.logger.info(f"Point Forecast: ${forecast_value:.2f}")
            
            return forecast_value
            
        except Exception as e:
            self.logger.error(f"Error in AutoTS prediction: {str(e)}")
            # Fallback to a simple prediction method if AutoTS fails
            self.logger.info("Using fallback prediction method")
            if hasattr(self, 'data') and self.data is not None:
                # Simple moving average fallback
                last_values = self.data['Weekly_Close'].values[-5:]  # Use last 5 values
                return float(np.mean(last_values))
            raise
