"""
Main script for running financial data scrapers.
"""
import os
import sys
from typing import List, Optional
from dotenv import load_dotenv

# Add the parent directory to the path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraping.constants import DEFAULT_START_DATE, DEFAULT_TICKERS
from scraping.scrapers import CompanyScraper, MarketScraper
from scraping.core.logger import setup_logging


class ScraperOrchestrator:
    """Orchestrates the execution of multiple scrapers."""
    
    def __init__(self, fred_api_key: Optional[str] = None):
        """Initialize the orchestrator.
        
        Args:
            fred_api_key: FRED API key for market data
        """
        self.fred_api_key = fred_api_key
        # Initialize logger only once at the application level
        self.logger = setup_logging()
    
    def run_company_scrapers(self, 
                           tickers: List[str], 
                           start_date: str = DEFAULT_START_DATE,
                           force: bool = False) -> None:
        """Run scrapers for multiple company tickers.
        
        Args:
            tickers: List of stock ticker symbols
            start_date: Start date for data fetching
            force: If True, skip user interaction and overwrite existing data
        """
        print(f"\nFetching company data for {len(tickers)} tickers...")
        
        for ticker in tickers:
            print(f"\nProcessing {ticker}...")
            try:
                scraper = CompanyScraper(ticker)
                success = scraper.save_company_data(start_date, force=force)
                
                if success:
                    print(f"✅ {ticker} data scraping completed successfully!")
                else:
                    print(f"❌ {ticker} data scraping failed!")
                    
            except Exception as e:
                print(f"❌ Error processing {ticker}: {e}")
    
    def run_market_scraper(self, 
                          start_date: str = DEFAULT_START_DATE,
                          force: bool = False) -> None:
        """Run market data scraper.
        
        Args:
            start_date: Start date for data fetching
            force: If True, skip user interaction and overwrite existing data
        """
        if not self.fred_api_key:
            print("❌ FRED API key not provided. Skipping market data scraping.")
            return
        
        print("\nFetching market data...")
        try:
            # Pass the logger to MarketScraper to prevent re-initializing logging
            scraper = MarketScraper(self.fred_api_key)
            success = scraper.save_market_data(start_date, force=force)
            
            if success:
                print("✅ Market data scraping completed successfully!")
            else:
                print("❌ Market data scraping failed!")
                
        except Exception as e:
            print(f"❌ Error processing market data: {e}")
    
    def run_all_scrapers(self, 
                        tickers: List[str] = DEFAULT_TICKERS,
                        start_date: str = DEFAULT_START_DATE,
                        force: bool = False,
                        include_market: bool = True) -> None:
        """Run all scrapers.
        
        Args:
            tickers: List of stock ticker symbols
            start_date: Start date for data fetching
            force: If True, skip user interaction and overwrite existing data
            include_market: Whether to include market data scraping
        """
        print("🚀 Starting financial data scraping...")
        
        # Run company scrapers
        self.run_company_scrapers(tickers, start_date, force)
        
        # Run market scraper if requested and API key is available
        if include_market:
            self.run_market_scraper(start_date, force)
        
        print("\n🎉 All scraping operations completed!")


def main():
    """Main function for command-line usage."""
    # Load environment variables
    load_dotenv()
    fred_api_key = os.getenv("FRED_API_KEY", "2ef79a6ddee11df7569ab749765d363b")
    
    # Initialize orchestrator
    orchestrator = ScraperOrchestrator(fred_api_key)
    
    # Run all scrapers with default settings
    orchestrator.run_all_scrapers(
        tickers=DEFAULT_TICKERS,
        start_date=DEFAULT_START_DATE,
        force=False,
        include_market=False  # Disabled for now as it was commented out in original
    )


if __name__ == "__main__":
    main()
