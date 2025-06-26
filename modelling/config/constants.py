"""Constants for the forecasting model."""
import os
from pathlib import Path

# Base paths
PROJECT_ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
MODELLING_DIR = PROJECT_ROOT / 'modelling'
SCRAPING_DIR = PROJECT_ROOT / 'scraping'

# Directory paths
CONFIG_DIR = MODELLING_DIR / 'config'
CACHE_DIR = MODELLING_DIR / 'cache'
PREDICTIONS_DIR = MODELLING_DIR / 'predictions'
SCRAPED_DATA_DIR = SCRAPING_DIR / 'scraped_data'

# Model config and cache paths
MODEL_CONFIG_PATH = CONFIG_DIR / 'model_config.json'
SARIMA_CACHE_DIR = CACHE_DIR / 'sarima_params'
TIMEMOE_CACHE_DIR = CACHE_DIR / 'time_moe_cache'

# Default parameters
DEFAULT_LOG_LEVEL = 'INFO'
DEFAULT_TEST_SIZE = 0.2
DEFAULT_PREDICTION_STEPS = 1

# Model names
MODEL_SARIMA = 'SARIMA'
MODEL_AUTOTS = 'AutoTS'
MODEL_TIMEMOE = 'TimeMOE'

# Date format for filenames
DATE_FORMAT = '%Y%m%d'
TIMESTAMP_FORMAT = '%Y%m%d_%H%M%S'
