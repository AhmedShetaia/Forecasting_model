"""
Constants and default configuration values for the forecasting application.
"""

import os

# Directory Paths
DEFAULT_BASE_DIR = "forecasting"
DEFAULT_DATA_DIR = os.path.join(DEFAULT_BASE_DIR, "data")
DEFAULT_INPUT_DIR = os.path.join(DEFAULT_DATA_DIR, "input")
DEFAULT_OUTPUT_DIR = os.path.join(DEFAULT_DATA_DIR, "output")

# External Data Sources
DEFAULT_PREDICTIONS_DIR = "modelling/predictions/"

# File Patterns
COMBINED_DATA_PATTERN = "combined_data_until_*.csv"
PREDICTIONS_PATTERN = "next_friday_predictions_*.json"
MARKET_DATA_DIR_PATTERN = "market_data_*"  # Pattern to match market_data_YYYYMMDD_YYYYMMDD directories
MARKET_DATA_FILENAME = "market_data.csv"   # Standard filename for market data

# Model Parameters
DEFAULT_RANDOM_STATE = 42
DEFAULT_CV_FOLDS = 5

# Logging
DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# Date Formats
DATE_FORMAT = "%Y%m%d"
