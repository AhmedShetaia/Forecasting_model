# Financial Data Scraper - Refactored

A clean, modular financial data scraping system for collecting stock prices and market data.

## 🏗️ Architecture

The refactored codebase follows clean architecture principles with clear separation of concerns:

```
scraping/
├── constants.py              # Configuration constants
├── main_refactored.py        # Main entry point
├── update_all_refactored.py  # Data update script
├── requirements_refactored.txt # Dependencies
├── .env.template            # Environment variables template
├── core/                    # Core utilities
│   ├── __init__.py
│   ├── logger.py           # Centralized logging
│   ├── file_manager.py     # File system operations
│   └── data_processor.py   # Data cleaning and processing
└── scrapers/               # Data scrapers
    ├── __init__.py
    ├── base_scraper.py     # Base class with common functionality
    ├── company_scraper.py  # Individual stock data scraper
    └── market_scraper.py   # Market-wide data scraper
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements_refactored.txt
```

### 2. Set Up Environment

```bash
cp .env.template .env
# Edit .env and add your FRED API key
```

### 3. Run the Scraper

```python
# Run all scrapers with default settings
python main_refactored.py

# Or use the orchestrator programmatically
from main_refactored import ScraperOrchestrator

orchestrator = ScraperOrchestrator(fred_api_key="your_key")
orchestrator.run_all_scrapers()
```

## 📊 Features

### Clean Code Principles Applied

- **Single Responsibility**: Each class has one clear purpose
- **DRY Principle**: Common functionality abstracted into base classes and utilities
- **Meaningful Names**: Descriptive variable and function names
- **Small Functions**: Functions focused on single tasks
- **Constants**: Magic numbers/strings replaced with named constants

### Modular Architecture

- **Base Scraper**: Common functionality for all scrapers
- **Specialized Scrapers**: Company and market-specific implementations
- **Core Utilities**: Reusable components for logging, file management, and data processing
- **Configuration**: Centralized constants and settings

### Error Handling

- Consistent error handling across all components
- Comprehensive logging with different levels
- Graceful degradation when data sources are unavailable

## 🔧 Usage Examples

### Scrape Individual Company Data

```python
from scrapers import CompanyScraper

# Create scraper for Apple stock
scraper = CompanyScraper("AAPL")

# Fetch and save data
success = scraper.save_company_data("2020-01-01")
```

### Scrape Market Data

```python
from scrapers import MarketScraper

# Create market data scraper
scraper = MarketScraper(fred_api_key="your_key")

# Fetch and save market data
success = scraper.save_market_data("2020-01-01")
```

### Update Existing Data

```python
from update_all_refactored import DataUpdater

# Update all existing data
updater = DataUpdater(fred_api_key="your_key")
updater.update_all_data()
```

## 🛠️ Development Tools

### Code Formatting

```bash
# Format code with black
black .

# Sort imports with isort
isort .
```

### Linting

```bash
# Check code style with flake8
flake8 .
```

## 📈 Data Sources

- **Stock Data**: Yahoo Finance (via yfinance)
- **Economic Data**: Federal Reserve Economic Data (FRED)
- **Market Indexes**: S&P 500, NASDAQ, VIX

## 🗂️ Output Structure

Data is organized in timestamped folders:

```
scraped_data/
├── AAPL_20200103_20250620/
│   └── AAPL_data.csv
├── market_data_20200103_20250620/
│   └── market_data.csv
└── ...
```

## 🔄 Key Improvements from Original

1. **Eliminated Code Duplication**: Common functionality moved to base classes
2. **Better Error Handling**: Consistent exception handling with proper logging
3. **Cleaner Data Processing**: Centralized data cleaning logic
4. **Modular Design**: Easy to extend with new data sources
5. **Configuration Management**: Constants separated from logic
6. **Type Hints**: Better code documentation and IDE support
7. **Environment Variables**: Secure API key management
8. **Standardized Logging**: Consistent logging across all components

## 📝 Configuration

Key settings in `constants.py`:

- `DEFAULT_TICKERS`: List of stock symbols to scrape
- `FRED_SERIES`: Economic indicators to fetch
- `MARKET_INDEXES`: Market indexes to track
- `OUTPUT_DIR`: Where to save data files

## 🧪 Testing

The modular design makes it easy to add unit tests:

```python
# Example test structure
tests/
├── test_company_scraper.py
├── test_market_scraper.py
├── test_data_processor.py
└── test_file_manager.py
```

## 🔮 Future Enhancements

- Add unit tests for all components
- Implement data validation schemas
- Add support for more data sources
- Create web dashboard for monitoring
- Add data quality checks
- Implement retry mechanisms for failed requests
