"""TimeMOE time series forecasting model implementation."""
import logging
import os
import numpy as np
import pandas as pd
import torch
from transformers import AutoModelForCausalLM
from .base_model import BaseTimeSeriesModel
from ..config.constants import TIMEMOE_CACHE_DIR

# Disable oneDNN optimizations which can cause issues with TimeMOE
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'


class TimeMOEPredictor(BaseTimeSeriesModel):
    """TimeMOE model for time series forecasting."""
    
    def __init__(self, cache_dir=None, log_level=logging.INFO):
        """Initialize the TimeMOE model.
        
        Args:
            cache_dir: Directory to cache the model
            log_level: Logging level
        """
        super().__init__(log_level)
        self.model = None
        self.cache_dir = cache_dir or TIMEMOE_CACHE_DIR
        self.data = None
        self.training_data = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.logger.info(f"Using device: {str(self.device)}")
        if self.cache_dir:
            self.logger.info(f"Using cache directory: {self.cache_dir}")
        # Don't initialize the model here, it will be lazy-loaded in train()
        # This avoids loading the large model until it's actually needed
    
    def _normalize_data(self, data):
        """Normalize the input data.
        
        Args:
            data: Data to normalize
            
        Returns:
            Tuple of (normalized_data, mean, std)
        """
        mean = data.mean()
        std = data.std()
        return (data - mean) / std, mean, std
    
    def train(self, data, **kwargs):
        """Prepare the predictor with the latest training data.
        
        The underlying TimeMOE model is very large, so we only load it **once** per
        `TimeMOEPredictor` instance to avoid repeated memory allocations that can
        lead to out-of-memory (OOM) errors during long rolling-window updates.
        
        Args:
            data: DataFrame with Date and Weekly_Close columns
            
        Returns:
            None
        """
        data = self._validate_data(data)
        
        # Store clean data for prediction
        self.data = data.copy()
        
        # Store the (sorted) series of prices for prediction
        if isinstance(data, pd.DataFrame):
            self.training_data = data.sort_values(by="Date")["Weekly_Close"].values
        else:
            self.training_data = data
        
        self.logger.info(f"TimeMOE prepared with {len(data)} data points")
        
        # Lazily load the model the first time `train` is called
        if self.model is None:
            self.logger.info("Loading TimeMOE model (this can take a while)...")
            try:
                self.model = AutoModelForCausalLM.from_pretrained(
                    "Maple728/TimeMoE-50M",
                    cache_dir=self.cache_dir,
                    trust_remote_code=True,
                    revision="main",
                )
                self.model.to(self.device)
                self.model.eval()  # inference mode – no gradients
                self.logger.info("TimeMOE model loaded successfully")
            except Exception as e:
                if "accelerate" in str(e):
                    # Give a more actionable error message if the dependency is missing
                    self.logger.error(
                        "The 'accelerate' package is required by the TimeMOE model. "
                        "Install it with:  pip install accelerate"
                    )
                    raise ImportError("Missing required package: accelerate") from e
                self.logger.warning(f"Failed to initialize TimeMOE model: {e}")
                self.model = None
    
    def predict(self, steps=1, seq_len=10, **kwargs):
        """Generate predictions using the TimeMOE model.
        
        Args:
            steps: Number of steps to forecast (ignored, TimeMOE predicts one step ahead)
            seq_len: Number of past data points to use for prediction
            
        Returns:
            Forecasted value
            
        Raises:
            ValueError: If model hasn't been loaded or data not prepared
        """
        if self.model is None:
            raise ValueError("TimeMOE model failed to initialize")
            
        if self.data is None and self.training_data is None:
            raise ValueError("Data must be prepared before making predictions")
            
        self.logger.info("Generating TimeMOE forecast...")
        
        try:
            # Use training data if available, otherwise use data
            data = self.training_data if self.training_data is not None else self.data['Weekly_Close'].values
            
            # Use the last seq_len points from the available data
            data = data[-seq_len:]
            
            # Convert to tensor and reshape
            seq = torch.FloatTensor(data).view(1, -1)
            seq = seq.to(self.device)
            
            # Normalize data
            normed_seq, mean, std = self._normalize_data(seq)
            
            self.logger.info("Starting TimeMOE prediction...")
            # Generate prediction
            with torch.no_grad():
                # Forward pass through the model
                outputs = self.model(normed_seq)
                # Get the last prediction
                if isinstance(outputs, tuple):
                    logits = outputs[0]
                else:
                    logits = outputs.logits if hasattr(outputs, 'logits') else outputs
                
                prediction = logits[0, -1].item()
                # Denormalize the prediction
                result = prediction * std + mean
                
                return result
                
        except Exception as e:
            self.logger.error(f"TimeMOE prediction error: {e}")
            raise
