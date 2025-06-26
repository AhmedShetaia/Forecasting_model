"""
Update script for refreshing existing financial data.
"""
import os
import re
from typing import Set
from dotenv import load_dotenv

from constants import OUTPUT_DIR, DEFAULT_START_DATE
from scrapers import CompanyScraper, MarketScraper
from core.logger import ScraperLogger


class DataUpdater:
    """Handles updating existing financial data."""
    
    def __init__(self, fred_api_key: str):
        """Initialize the data updater.
        
        Args:
            fred_api_key: FRED API key for market data
        """
        self.fred_api_key = fred_api_key
        self.logger = ScraperLogger.get_logger("DataUpdater")
    
    def _extract_ticker_from_folder(self, folder_name: str) -> str:
        """Extract ticker symbol from folder name.
        
        Args:
            folder_name: Folder name in format "TICKER_YYYYMMDD_YYYYMMDD"
            
        Returns:
            Ticker symbol or None if not found
        """
        match = re.match(r"([A-Z]+)_\d{8}_\d{8}$", folder_name)
        return match.group(1) if match else None
    
    def _discover_existing_tickers(self) -> Set[str]:
        """Discover ticker symbols from existing data folders.
        
        Returns:
            Set of ticker symbols that have existing data
        """
        tickers = set()
        
        if not os.path.exists(OUTPUT_DIR):
            return tickers
        
        for entry in os.listdir(OUTPUT_DIR):
            ticker = self._extract_ticker_from_folder(entry)
            if ticker:
                tickers.add(ticker)
        
        return tickers
    
    def update_market_data(self) -> bool:
        """Update market data.
        
        Returns:
            True if successful, False otherwise
        """
        print("📈 Updating market data...")
        try:
            scraper = MarketScraper(self.fred_api_key)
            success = scraper.update_data()
            
            if success:
                print("✅ Market data update completed!")
            else:
                print("ℹ️ Market data update not needed or failed")
            
            return success
        except Exception as e:
            print(f"❌ Error updating market data: {e}")
            return False
    
    def update_company_data(self, tickers: Set[str]) -> None:
        """Update company data for multiple tickers.
        
        Args:
            tickers: Set of ticker symbols to update
        """
        print(f"📊 Updating company data for {len(tickers)} tickers...")
        
        for ticker in sorted(tickers):
            print(f"Updating {ticker}...")
            try:
                scraper = CompanyScraper(ticker)
                success = scraper.update_data()
                
                if success:
                    print(f"✅ {ticker} update completed!")
                else:
                    print(f"ℹ️ {ticker} update not needed or failed")
                    
            except Exception as e:
                print(f"❌ Error updating {ticker}: {e}")
    
    def update_all_data(self, include_market: bool = True) -> None:
        """Update all existing data.
        
        Args:
            include_market: Whether to include market data updates
        """
        print("🔄 Starting data update process...")
        
        # Update market data first
        if include_market:
            self.update_market_data()
        
        # Discover and update company data
        existing_tickers = self._discover_existing_tickers()
        if existing_tickers:
            self.update_company_data(existing_tickers)
        else:
            print("ℹ️ No existing company data folders found")
        
        print("🎉 All updates completed!")


def main():
    """Main function for updating data."""
    # Load environment variables
    load_dotenv()
    fred_api_key = os.getenv("FRED_API_KEY")
    
    if not fred_api_key:
        print("❌ FRED_API_KEY not found in environment variables")
        return
    
    # Initialize and run updater
    updater = DataUpdater(fred_api_key)
    updater.update_all_data(include_market=True)


if __name__ == "__main__":
    main()
