# Financial Forecasting System

A comprehensive system for scraping financial data, building predictive models, and forecasting future stock prices.

## 📋 Overview

This system is comprised of three main components:

1. **Scraping Module**: Collects financial data from various sources
2. **Modeling Module**: Processes data and builds predictive models
3. **Forecasting Module**: Generates forecasts based on models and provides final output

The system is designed to be run as a complete pipeline or as individual components depending on your needs.

## 🏗️ Project Structure

```
financial-forecasting/
├── scraping/              # Financial data scraper
│   ├── core/              # Core utilities
│   ├── scrapers/          # Data scrapers
│   ├── constants.py       # Configuration constants
│   ├── main.py            # Main entry point
│   └── update_all.py      # Update existing data
├── modelling/             # Time series modeling
│   ├── models/            # Model implementations
│   ├── utils/             # Utility functions
│   ├── config/            # Configuration
│   ├── predictions/       # Model predictions
│   └── update_predictions.py # Update prediction files
├── forecasting/           # Final forecasting system
│   ├── src/               # Source code
│   ├── data/              # Data files
│   └── main.py            # Main entry point
├── run_pipeline.py        # Complete pipeline orchestrator
├── requirements.txt       # Consolidated dependencies
└── Dockerfile             # Container definition
```

## 🚀 Quick Start

### Using Docker

1. Build the Docker image:
   ```bash
   docker build -t financial-forecasting .
   ```

2. Run the complete pipeline:
   ```bash
   docker run -v ./data:/app/scraping/scraped_data -e FRED_API_KEY=your_api_key financial-forecasting
   ```

### Manual Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create .env file with your API keys:
   ```
   FRED_API_KEY=your_fred_api_key_here
   ```

3. Run the complete pipeline:
   ```bash
   python run_pipeline.py
   ```

## ⚙️ Configuration

### Environment Variables

- `FRED_API_KEY`: API key for Federal Reserve Economic Data (required for market data)

### Command Line Options

The main pipeline script accepts the following arguments:

```bash
python run_pipeline.py [options]
```

Options:
- `--skip-scraping`: Skip the data scraping step
- `--skip-modeling`: Skip the modeling step
- `--skip-forecasting`: Skip the forecasting step
- `--log-level`: Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## 🧩 Components

### Scraping Module

The scraping module collects financial data from various sources including stock prices and market indicators.

Key features:
- Individual stock data collection
- Market-wide indicators collection
- Incremental updates
- Robust error handling

To run independently:
```bash
python -m scraping.update_all
```

### Modeling Module

The modeling module processes scraped data and builds predictive models using various time series forecasting techniques.

Supported models:
- SARIMA (Seasonal AutoRegressive Integrated Moving Average)
- AutoTS (Automated Time Series model selection)
- TimeMOE (Transformer-based time series forecasting)

To run independently:
```bash
python -m modelling.update_predictions
```

### Forecasting Module

The forecasting module combines model predictions with additional features to generate final forecasts.

Key features:
- Data preparation and feature engineering
- Model evaluation and selection
- Comprehensive error metrics
- JSON output for next week predictions

To run independently:
```bash
python -m forecasting.main
```

## 📊 Data Flow

1. **Scraping**: Raw financial data is collected and saved to `scraping/scraped_data/`
2. **Modeling**: Models are trained on scraped data and predictions are saved to `modelling/predictions/`
3. **Forecasting**: Final forecasts are generated using model predictions and saved to `forecasting/data/`

## 🔄 Updating Existing Data

To update existing data without starting from scratch:

```bash
python run_pipeline.py
```

The system is designed to automatically detect existing data and update it with the latest information.

## 📝 License

[MIT License](LICENSE)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
