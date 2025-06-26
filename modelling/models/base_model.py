"""Base class for time series forecasting models."""
import logging
from abc import ABC, abstractmethod
import pandas as pd


class BaseTimeSeriesModel(ABC):
    """Abstract base class for all time series forecasting models.
    
    All model implementations should inherit from this class and implement
    the required methods.
    """
    
    def __init__(self, log_level=logging.INFO):
        """Initialize the model with logging configuration.
        
        Args:
            log_level: The logging level to use (e.g., logging.INFO, logging.DEBUG)
        """
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.logger.setLevel(log_level)
    
    @abstractmethod
    def train(self, data: pd.DataFrame, **kwargs):
        """Train the model on historical time series data.
        
        Args:
            data: DataFrame containing time series data with at least Date and Weekly_Close columns
            **kwargs: Additional model-specific parameters
            
        Returns:
            None
        """
        pass
    
    @abstractmethod
    def predict(self, steps=1, **kwargs):
        """Generate forecasts for future time periods.
        
        Args:
            steps: Number of time periods to forecast
            **kwargs: Additional model-specific parameters
            
        Returns:
            Forecast value(s)
        """
        pass
    
    def _validate_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Validate and prepare input data.
        
        Args:
            data: Input DataFrame
            
        Returns:
            Validated and prepared DataFrame
            
        Raises:
            ValueError: If data format is invalid
        """
        required_cols = ['Date', 'Weekly_Close']
        
        # Check if data is a DataFrame
        if not isinstance(data, pd.DataFrame):
            raise ValueError("Input data must be a pandas DataFrame")
            
        # Check for required columns
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            raise ValueError(f"Input data is missing required columns: {missing_cols}")
            
        # Ensure Date column is datetime
        if not pd.api.types.is_datetime64_any_dtype(data['Date']):
            data['Date'] = pd.to_datetime(data['Date'])
            
        # Ensure data is sorted by date
        return data.sort_values('Date').reset_index(drop=True)
