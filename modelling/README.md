# Time Series Forecasting Model

This project implements several time series forecasting models to predict future stock prices for different companies.

## Project Structure

```
modelling_refactored/
│
├── config/                 # Configuration files
│   ├── __init__.py
│   ├── constants.py        # Project-wide constants and paths
│   └── model_config.json   # Model hyperparameters
│
├── models/                 # Model implementations
│   ├── __init__.py
│   ├── base_model.py       # Abstract base class for models
│   ├── sarima_model.py     # SARIMA model implementation
│   ├── autots_model.py     # AutoTS model implementation
│   └── timemoe_model.py    # TimeMOE model implementation
│
├── utils/                  # Utility functions
│   ├── __init__.py
│   ├── data_processor.py   # Data loading and preparation
│   ├── file_utils.py       # File handling utilities
│   └── model_trainer.py    # Model training orchestration
│
├── cache/                  # Model cache storage
│   ├── sarima_params/      # SARIMA model parameters cache
│   └── time_moe_cache/     # TimeMOE model cache
│
├── predictions/            # Prediction outputs
│
├── train_models.py         # Main script to train models for a company
└── update_predictions.py   # Script to update existing predictions
```

## Models

The project implements three forecasting models:

1. **SARIMA**: Seasonal AutoRegressive Integrated Moving Average
2. **AutoTS**: Automated Time Series model selection and ensembling
3. **TimeMOE**: Transformer-based time series forecasting model

## Usage

### Training Models

To train models for a specific company:

```bash
python -m modelling_refactored.train_models --ticker AAPL
```

Options:
- `--ticker`: Company ticker symbol (required)
- `--test-run`: Run on a small subset of data for quick testing
- `--cache-dir`: Directory to cache the TimeMOE model
- `--scraped-folder`: Path to folder containing scraped data
- `--config-path`: Path to model configuration file
- `--output-dir`: Directory to save predictions
- `--log-level`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Updating Predictions

To update all prediction files with new data:

```bash
python -m modelling_refactored.update_predictions
```

To update a specific prediction file:

```bash
python -m modelling_refactored.update_predictions --single-file path/to/predictions.csv
```

Options:
- `--pred-dir`: Directory containing prediction files
- `--scraped-folder`: Path to folder containing scraped data
- `--cache-dir`: Directory to cache the TimeMOE model
- `--ticker`: Force using a specific ticker symbol
- `--single-file`: Path to a specific prediction file to update
- `--log-level`: Logging level

## Dependencies

Required packages:
- pandas
- numpy
- pmdarima
- statsmodels
- autots
- transformers (for TimeMOE)
- tqdm

See `requirements.txt` for the complete list.

## License

[Specify your license]
