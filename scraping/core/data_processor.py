"""
Data processing utilities for financial data cleaning and transformation.
"""
import pandas as pd
from typing import Dict, Optional
import warnings

from constants import (
    WEEKLY_FREQUENCY, DATE_COLUMN, WEEKLY_CLOSE_COLUMN, 
    DEFAULT_RESAMPLE_METHOD, MARKET_INDEXES
)

# Suppress FutureWarning from various libraries
warnings.filterwarnings("ignore", category=FutureWarning)


class DataProcessor:
    """Handles common data processing operations for financial data."""
    
    @staticmethod
    def normalize_timezone(df: pd.DataFrame) -> pd.DataFrame:
        """Remove timezone information from DataFrame index if present.
        
        Args:
            df: DataFrame with potentially timezone-aware index
            
        Returns:
            DataFrame with timezone-naive index
        """
        if hasattr(df.index, 'tz') and df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        return df
    
    @staticmethod
    def resample_to_weekly(df: pd.DataFrame, 
                          close_column: str = 'Close',
                          method: str = DEFAULT_RESAMPLE_METHOD) -> pd.DataFrame:
        """Resample daily data to weekly frequency ending on Friday.
        
        Args:
            df: DataFrame with daily data
            close_column: Name of the close price column
            method: Resampling method ('last', 'mean', etc.)
            
        Returns:
            DataFrame resampled to weekly frequency
        """
        df = DataProcessor.normalize_timezone(df)
        df.index.name = DATE_COLUMN
        
        # Select only close price and resample
        weekly_df = df[[close_column]].resample(WEEKLY_FREQUENCY).agg(method)
        
        # Reset index and rename columns
        weekly_df = weekly_df.reset_index()
        weekly_df = weekly_df.rename(columns={close_column: WEEKLY_CLOSE_COLUMN})
        
        return weekly_df
    
    @staticmethod
    def clean_market_data_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize market data column names.
        
        Args:
            df: DataFrame with potentially messy column names
            
        Returns:
            DataFrame with cleaned column names
        """
        if df.empty:
            return df
        
        # Handle MultiIndex columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join([str(i) for i in tup if i]) for tup in df.columns]
        
        # Create rename mapping for legacy columns
        rename_map = {}
        
        for col in df.columns:
            # Handle tuple columns from multi-index
            if isinstance(col, tuple):
                rename_map[col] = col[0]
                continue
                
            # Handle legacy tuple-string columns
            if isinstance(col, str) and col.strip().startswith('(') and ',' in col:
                cleaned = col.split(',')[0]
                cleaned = cleaned.replace("('", '').replace("(", '').replace("'", '').strip()
                rename_map[col] = cleaned
                continue
                
            # Handle flattened columns with dots
            if isinstance(col, str) and '.' in col:
                prefix = col.split('.')[0]
                rename_map[col] = prefix
                continue
                
            # Remove market index suffixes
            if isinstance(col, str):
                for symbol in MARKET_INDEXES.values():
                    suffix = f"_{symbol}"
                    if col.endswith(suffix):
                        rename_map[col] = col[:-len(suffix)]
                        break
        
        # Apply renaming
        if rename_map:
            df = df.rename(columns=rename_map)
        
        # Remove duplicate date columns (keep only 'Date')
        duplicate_date_cols = [
            col for col in df.columns 
            if col != DATE_COLUMN and str(col).lower().startswith('date')
        ]
        if duplicate_date_cols:
            df = df.drop(columns=duplicate_date_cols)
        
        # Remove duplicate columns
        df = df.loc[:, ~df.columns.duplicated()]
        
        return df
    
    @staticmethod
    def normalize_dates(df: pd.DataFrame, date_column: str = DATE_COLUMN) -> pd.DataFrame:
        """Normalize dates and remove duplicate entries.
        
        Args:
            df: DataFrame with date column
            date_column: Name of the date column
            
        Returns:
            DataFrame with normalized dates and no duplicates
        """
        if df.empty or date_column not in df.columns:
            return df
        
        # Normalize dates
        df[date_column] = pd.to_datetime(df[date_column]).dt.normalize()
        
        # Sort by date and remove duplicates, keeping the last entry
        df = df.sort_values(date_column).drop_duplicates(
            subset=[date_column], keep='last'
        ).reset_index(drop=True)
        
        return df
    
    @staticmethod
    def merge_dataframes(*dataframes: pd.DataFrame, 
                        on_column: str = DATE_COLUMN,
                        how: str = 'outer') -> pd.DataFrame:
        """Merge multiple dataframes on a common column.
        
        Args:
            *dataframes: Variable number of DataFrames to merge
            on_column: Column to merge on
            how: Type of merge ('outer', 'inner', etc.)
            
        Returns:
            Merged DataFrame
        """
        if not dataframes:
            return pd.DataFrame()
        
        # Filter out empty dataframes
        valid_dfs = [df for df in dataframes if not df.empty]
        
        if not valid_dfs:
            return pd.DataFrame(columns=[on_column])
        
        if len(valid_dfs) == 1:
            return valid_dfs[0]
        
        # Merge dataframes sequentially
        result = valid_dfs[0]
        for df in valid_dfs[1:]:
            result = pd.merge(result, df, on=on_column, how=how)
        
        # Sort by the merge column and forward fill missing values
        result = result.sort_values(on_column).fillna(method='ffill')
        
        return result.reset_index(drop=True)
