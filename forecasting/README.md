# Forecasting Model

A Python-based financial forecasting system that combines market data with model predictions to forecast stock prices.

## Project Structure

```
forecasting/
├── data/                   # Data directory
│   ├── input/              # Input data files
│   └── output/             # Output data files
├── src/                    # Source code
│   ├── config/             # Configuration and constants
│   ├── data_preparation/   # Data preparation modules
│   ├── modeling/           # Model training and prediction modules
│   └── utils/              # Utility functions
├── tests/                  # Unit tests
├── main.py                 # Main entry point
└── requirements.txt        # Project dependencies
```

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd forecasting-model
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
venv\Scripts\activate  # On Windows
source venv/bin/activate  # On Unix/Mac
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Running the full pipeline

```bash
python main.py
```

### Running individual steps

**Data Preparation Only:**
```bash
python main.py --skip-training
```

**Model Training Only:**
```bash
python main.py --skip-data-prep
```

### Command Line Options

- `--log-level`: Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--skip-data-prep`: Skip the data preparation step
- `--skip-training`: Skip the model training step
- `--data-dir`: Specify an alternative directory for data files (both input and output)
- `--input-dir`: Optionally specify a separate input directory (if different from data-dir)

### Directory Structure

The application uses the following directory structure for data:

```
forecasting/
├── data/
│   ├── input/    # Raw input data files (company data, market data)
│   └── output/   # Generated output files (combined data, predictions)
```

By default, the application looks for input files and saves output files to `forecasting/data/output`. 
You can use the command line options to customize these locations.

## Testing

Run the tests with:

```bash
pytest tests/
```

## Data

The system expects:

1. Model prediction CSV files in the `modelling/predictions/` directory
2. Market data in `scraping/scraped_data/market_data_YYYYMMDD_YYYYMMDD/market_data.csv` files
   - The system automatically finds the latest market data directory based on the end date in the directory name

## Data Flow

The system uses the following data flow:

1. **Input Data**:
   - Model prediction CSV files from `modelling/predictions/`
   - Market data from `scraping/scraped_data/market_data_YYYYMMDD_YYYYMMDD/market_data.csv`

2. **Intermediate Data**:
   - Combined data files (`combined_data_until_YYYYMMDD.csv`) saved to `data/output/` directory
   - These files are both outputs of the data preparation step and inputs to the model training step

3. **Final Output**:
   - Stock price predictions for the next Friday in a JSON file named `next_friday_predictions_YYYYMMDD.json`
   - Saved to `data/output/` directory
