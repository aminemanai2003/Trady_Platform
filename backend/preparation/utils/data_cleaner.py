"""
Data Cleaner Module
Handles data cleaning, missing values, outliers, and normalization
"""

import pandas as pd
import numpy as np
from loguru import logger
from typing import Dict, List, Optional, Tuple
import sys

# Configure logger
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")


class DataCleaner:
    """Clean and preprocess data"""
    
    def __init__(self, outlier_std_threshold: float = 3.0, max_missing_ratio: float = 0.05):
        """
        Initialize DataCleaner
        
        Args:
            outlier_std_threshold: Number of std deviations for outlier detection
            max_missing_ratio: Maximum ratio of missing values allowed
        """
        self.outlier_std_threshold = outlier_std_threshold
        self.max_missing_ratio = max_missing_ratio
        self.cleaning_report = {}
    
    def analyze_missing_values(self, df: pd.DataFrame) -> Dict:
        """
        Analyze missing values in DataFrame
        
        Args:
            df: Input DataFrame
            
        Returns:
            Dictionary with missing value statistics
        """
        logger.info("Analyzing missing values...")
        
        total_rows = len(df)
        missing_info = {}
        
        for col in df.columns:
            missing_count = df[col].isna().sum()
            missing_ratio = missing_count / total_rows
            
            if missing_count > 0:
                missing_info[col] = {
                    'count': int(missing_count),
                    'ratio': float(missing_ratio),
                    'ratio_pct': f"{missing_ratio*100:.2f}%"
                }
        
        if missing_info:
            logger.warning(f"Found missing values in {len(missing_info)} columns")
            for col, info in missing_info.items():
                logger.warning(f"  {col}: {info['count']} ({info['ratio_pct']})")
        else:
            logger.info("✓ No missing values found")
        
        return missing_info
    
    def handle_missing_values(self, df: pd.DataFrame, strategy: str = 'auto') -> pd.DataFrame:
        """
        Handle missing values in DataFrame
        
        Args:
            df: Input DataFrame
            strategy: 'forward_fill', 'backward_fill', 'interpolate', 'drop', 'auto'
            
        Returns:
            Cleaned DataFrame
        """
        logger.info(f"Handling missing values (strategy: {strategy})...")
        
        df_clean = df.copy()
        original_rows = len(df_clean)
        
        # Analyze missing values first
        missing_info = self.analyze_missing_values(df_clean)
        
        if not missing_info:
            return df_clean
        
        # Apply strategy
        if strategy == 'forward_fill':
            df_clean = df_clean.fillna(method='ffill')
        
        elif strategy == 'backward_fill':
            df_clean = df_clean.fillna(method='bfill')
        
        elif strategy == 'interpolate':
            # Interpolate numeric columns
            numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
            df_clean[numeric_cols] = df_clean[numeric_cols].interpolate(method='linear')
        
        elif strategy == 'drop':
            df_clean = df_clean.dropna()
        
        elif strategy == 'auto':
            # Smart strategy based on column type and missing ratio
            for col, info in missing_info.items():
                if info['ratio'] > self.max_missing_ratio:
                    # Too many missing values - drop column
                    logger.warning(f"  Dropping column {col} (missing ratio {info['ratio_pct']} > threshold)")
                    df_clean = df_clean.drop(columns=[col])
                else:
                    # Reasonable amount - interpolate or forward fill
                    if df_clean[col].dtype in [np.float64, np.int64]:
                        df_clean[col] = df_clean[col].interpolate(method='linear')
                        df_clean[col] = df_clean[col].fillna(method='ffill').fillna(method='bfill')
                    else:
                        df_clean[col] = df_clean[col].fillna(method='ffill').fillna(method='bfill')
        
        # Remove any remaining NaN rows
        df_clean = df_clean.dropna()
        
        removed_rows = original_rows - len(df_clean)
        if removed_rows > 0:
            logger.info(f"✓ Removed {removed_rows} rows with missing values")
        
        logger.info(f"✓ Missing values handled: {original_rows} → {len(df_clean)} rows")
        
        return df_clean
    
    def detect_outliers(self, df: pd.DataFrame, columns: Optional[List[str]] = None) -> Dict:
        """
        Detect outliers using statistical methods
        
        Args:
            df: Input DataFrame
            columns: List of columns to check (None = all numeric)
            
        Returns:
            Dictionary with outlier information
        """
        logger.info("Detecting outliers...")
        
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        outlier_info = {}
        
        for col in columns:
            if col not in df.columns:
                continue
            
            # Z-score method
            mean = df[col].mean()
            std = df[col].std()
            
            if std == 0:
                continue
            
            z_scores = np.abs((df[col] - mean) / std)
            outliers = z_scores > self.outlier_std_threshold
            outlier_count = outliers.sum()
            
            if outlier_count > 0:
                outlier_info[col] = {
                    'count': int(outlier_count),
                    'ratio': float(outlier_count / len(df)),
                    'ratio_pct': f"{(outlier_count / len(df))*100:.2f}%",
                    'min': float(df[col].min()),
                    'max': float(df[col].max()),
                    'mean': float(mean),
                    'std': float(std)
                }
        
        if outlier_info:
            logger.warning(f"Found outliers in {len(outlier_info)} columns")
            for col, info in outlier_info.items():
                logger.warning(f"  {col}: {info['count']} outliers ({info['ratio_pct']})")
        else:
            logger.info("✓ No significant outliers detected")
        
        return outlier_info
    
    def handle_outliers(self, df: pd.DataFrame, strategy: str = 'cap', columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Handle outliers in DataFrame
        
        Args:
            df: Input DataFrame
            strategy: 'cap', 'remove', 'transform', 'none'
            columns: List of columns to process (None = all numeric)
            
        Returns:
            Cleaned DataFrame
        """
        logger.info(f"Handling outliers (strategy: {strategy})...")
        
        if strategy == 'none':
            return df.copy()
        
        df_clean = df.copy()
        
        if columns is None:
            columns = df_clean.select_dtypes(include=[np.number]).columns.tolist()
        
        outliers_handled = 0
        
        for col in columns:
            if col not in df_clean.columns:
                continue
            
            # Calculate bounds
            mean = df_clean[col].mean()
            std = df_clean[col].std()
            
            if std == 0:
                continue
            
            lower_bound = mean - (self.outlier_std_threshold * std)
            upper_bound = mean + (self.outlier_std_threshold * std)
            
            # Identify outliers
            outliers = (df_clean[col] < lower_bound) | (df_clean[col] > upper_bound)
            outlier_count = outliers.sum()
            
            if outlier_count == 0:
                continue
            
            if strategy == 'cap':
                # Cap values at bounds
                df_clean.loc[df_clean[col] < lower_bound, col] = lower_bound
                df_clean.loc[df_clean[col] > upper_bound, col] = upper_bound
                outliers_handled += outlier_count
            
            elif strategy == 'remove':
                # Remove rows with outliers
                df_clean = df_clean[~outliers]
                outliers_handled += outlier_count
            
            elif strategy == 'transform':
                # Winsorize (replace with percentiles)
                lower_percentile = df_clean[col].quantile(0.01)
                upper_percentile = df_clean[col].quantile(0.99)
                df_clean.loc[df_clean[col] < lower_percentile, col] = lower_percentile
                df_clean.loc[df_clean[col] > upper_percentile, col] = upper_percentile
                outliers_handled += outlier_count
        
        if outliers_handled > 0:
            logger.info(f"✓ Handled {outliers_handled} outlier values")
        
        return df_clean
    
    def remove_duplicates(self, df: pd.DataFrame, subset: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Remove duplicate rows
        
        Args:
            df: Input DataFrame
            subset: Columns to consider for duplicates (None = all)
            
        Returns:
            DataFrame without duplicates
        """
        logger.info("Removing duplicates...")
        
        original_rows = len(df)
        df_clean = df.drop_duplicates(subset=subset, keep='first')
        duplicates_removed = original_rows - len(df_clean)
        
        if duplicates_removed > 0:
            logger.warning(f"✓ Removed {duplicates_removed} duplicate rows")
        else:
            logger.info("✓ No duplicates found")
        
        return df_clean
    
    def normalize_data(self, df: pd.DataFrame, columns: Optional[List[str]] = None, method: str = 'standard') -> Tuple[pd.DataFrame, Dict]:
        """
        Normalize numeric columns
        
        Args:
            df: Input DataFrame
            columns: Columns to normalize (None = all numeric)
            method: 'standard' (z-score), 'minmax', 'robust'
            
        Returns:
            Tuple of (normalized DataFrame, scaling parameters)
        """
        logger.info(f"Normalizing data (method: {method})...")
        
        df_norm = df.copy()
        
        if columns is None:
            columns = df_norm.select_dtypes(include=[np.number]).columns.tolist()
        
        scaling_params = {}
        
        for col in columns:
            if col not in df_norm.columns:
                continue
            
            if method == 'standard':
                # Z-score normalization
                mean = df_norm[col].mean()
                std = df_norm[col].std()
                if std != 0:
                    df_norm[col] = (df_norm[col] - mean) / std
                    scaling_params[col] = {'method': 'standard', 'mean': float(mean), 'std': float(std)}
            
            elif method == 'minmax':
                # Min-max scaling to [0, 1]
                min_val = df_norm[col].min()
                max_val = df_norm[col].max()
                if max_val != min_val:
                    df_norm[col] = (df_norm[col] - min_val) / (max_val - min_val)
                    scaling_params[col] = {'method': 'minmax', 'min': float(min_val), 'max': float(max_val)}
            
            elif method == 'robust':
                # Robust scaling using median and IQR
                median = df_norm[col].median()
                q1 = df_norm[col].quantile(0.25)
                q3 = df_norm[col].quantile(0.75)
                iqr = q3 - q1
                if iqr != 0:
                    df_norm[col] = (df_norm[col] - median) / iqr
                    scaling_params[col] = {'method': 'robust', 'median': float(median), 'iqr': float(iqr)}
        
        logger.info(f"✓ Normalized {len(scaling_params)} columns")
        
        return df_norm, scaling_params
    
    def clean_economic_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean economic indicator data
        
        Args:
            df: Economic indicators DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        logger.info("=" * 60)
        logger.info("CLEANING ECONOMIC DATA")
        logger.info("=" * 60)
        
        df_clean = df.copy()
        
        # 1. Remove duplicates
        df_clean = self.remove_duplicates(df_clean, subset=['date', 'series_id'])
        
        # 2. Handle missing values
        df_clean = self.handle_missing_values(df_clean, strategy='interpolate')
        
        # 3. Detect and handle outliers
        outliers = self.detect_outliers(df_clean, columns=['value'])
        df_clean = self.handle_outliers(df_clean, strategy='cap', columns=['value'])
        
        # 4. Sort by date
        df_clean = df_clean.sort_values(['series_id', 'date']).reset_index(drop=True)
        
        logger.info("=" * 60)
        logger.info(f"✓ ECONOMIC DATA CLEANED: {len(df)} → {len(df_clean)} rows")
        logger.info("=" * 60)
        
        return df_clean
    
    def clean_ohlc_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean OHLC price data
        
        Args:
            df: OHLC DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        logger.info("=" * 60)
        logger.info("CLEANING OHLC DATA")
        logger.info("=" * 60)
        
        df_clean = df.copy()
        
        # 1. Remove duplicates based on timestamp
        df_clean = self.remove_duplicates(df_clean, subset=['time', 'symbol', 'timeframe'])
        
        # 2. Validate OHLC relationships
        invalid_ohlc = (
            (df_clean['high'] < df_clean['low']) |
            (df_clean['high'] < df_clean['open']) |
            (df_clean['high'] < df_clean['close']) |
            (df_clean['low'] > df_clean['open']) |
            (df_clean['low'] > df_clean['close'])
        )
        
        if invalid_ohlc.sum() > 0:
            logger.warning(f"Found {invalid_ohlc.sum()} invalid OHLC relationships - removing")
            df_clean = df_clean[~invalid_ohlc]
        
        # 3. Handle missing values (forward fill for prices)
        df_clean = self.handle_missing_values(df_clean, strategy='forward_fill')
        
        # 4. Detect outliers in price movements
        price_cols = ['open', 'high', 'low', 'close']
        outliers = self.detect_outliers(df_clean, columns=price_cols)
        
        # 5. Sort by time
        df_clean = df_clean.sort_values('time').reset_index(drop=True)
        
        logger.info("=" * 60)
        logger.info(f"✓ OHLC DATA CLEANED: {len(df)} → {len(df_clean)} rows")
        logger.info("=" * 60)
        
        return df_clean
    
    def get_cleaning_summary(self) -> Dict:
        """Get summary of cleaning operations"""
        return self.cleaning_report.copy()


if __name__ == '__main__':
    # Test the DataCleaner
    
    # Create sample data with issues
    data = {
        'date': pd.date_range('2020-01-01', periods=100, freq='D'),
        'value': np.random.randn(100) * 10 + 100
    }
    
    # Add some missing values
    data['value'][10:15] = np.nan
    
    # Add some outliers
    data['value'][50] = 1000
    data['value'][51] = -500
    
    df_test = pd.DataFrame(data)
    
    print("\n" + "=" * 60)
    print("TESTING DATA CLEANER")
    print("=" * 60)
    
    cleaner = DataCleaner(outlier_std_threshold=3.0, max_missing_ratio=0.10)
    
    # Analyze
    missing = cleaner.analyze_missing_values(df_test)
    outliers = cleaner.detect_outliers(df_test)
    
    # Clean
    df_cleaned = cleaner.handle_missing_values(df_test, strategy='interpolate')
    df_cleaned = cleaner.handle_outliers(df_cleaned, strategy='cap')
    
    print(f"\nOriginal rows: {len(df_test)}")
    print(f"Cleaned rows: {len(df_cleaned)}")
    print("=" * 60)
