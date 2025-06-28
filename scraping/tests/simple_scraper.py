from dotenv import load_dotenv
import os
from constants import DEFAULT_TICKERS, DEFAULT_START_DATE
from main import ScraperOrchestrator
from scraping.core.date_utils import get_last_trading_friday

# Get safe end date (last trading Friday)
safe_end_date = get_last_trading_friday()

# Load environment variables
load_dotenv()
fred_api_key = os.getenv("FRED_API_KEY")

# Initialize orchestrator
orchestrator = ScraperOrchestrator(fred_api_key)

# Run scraper for AAPL with safe date range
print("📊 Starting AAPL data scraping...")
orchestrator.run_company_scrapers(
    tickers=['AAPL'],  # Single ticker
    start_date=DEFAULT_START_DATE,
    force=True,  # Skip user prompts for testing
)