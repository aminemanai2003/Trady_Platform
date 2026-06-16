"""
03_engineer_features.py
Feature Engineering Pipeline for Forex Alpha Data
Calculates technical indicators and engineered features
"""

import pandas as pd
import sys
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config import PROCESSED_DATA_DIR, OUTPUT_DIR, FEATURE_CONFIG
from utils import FeatureCalculator
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")
logger.add(OUTPUT_DIR / "feature_engineering.log", rotation="10 MB")


def engineer_ohlc_features(symbol: str, timeframe: str = '1D'):
    """
    Engineer features for OHLC price data
    
    Args:
        symbol: Currency pair symbol
        timeframe: Timeframe
        
    Returns:
        Dict with engineering summary
    """
    logger.info(f"Engineering features for {symbol} {timeframe}...")
    
    # Load cleaned data
    filename = f'ohlc_{symbol}_{timeframe}_clean.parquet'
    input_path = PROCESSED_DATA_DIR / filename
    
    if not input_path.exists():
        logger.warning(f"  ⚠ File not found: {input_path}")
        return None
    
    df_clean = pd.read_parquet(input_path)
    logger.info(f"  Loaded {len(df_clean):,} candles")
    
    # Initialize feature calculator
    calculator = FeatureCalculator()
    
    # Calculate all technical features
    df_features = calculator.calculate_all_features(df_clean, config=FEATURE_CONFIG)
    
    # Remove rows with NaN (from indicator calculations)
    original_rows = len(df_features)
    df_features = df_features.dropna()
    rows_removed = original_rows - len(df_features)
    
    logger.info(f"  Removed {rows_removed} rows with NaN from feature calculations")
    
    # Save feature-engineered data
    output_filename = f'ohlc_{symbol}_{timeframe}_features.parquet'
    output_path = PROCESSED_DATA_DIR / output_filename
    df_features.to_parquet(output_path, index=False)
    logger.info(f"  ✓ Saved: {output_path}")
    
    # Also save feature list
    feature_list_path = OUTPUT_DIR / f'features_{symbol}_{timeframe}.txt'
    with open(feature_list_path, 'w') as f:
        f.write(f"Features for {symbol} {timeframe}\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Total Features: {len(calculator.get_feature_list())}\n\n")
        for i, feat in enumerate(calculator.get_feature_list(), 1):
            f.write(f"{i:3d}. {feat}\n")
    
    logger.info(f"  ✓ Saved feature list: {feature_list_path}")
    
    # Summary
    summary = {
        'symbol': symbol,
        'timeframe': timeframe,
        'input_rows': len(df_clean),
        'output_rows': len(df_features),
        'total_columns': len(df_features.columns),
        'feature_columns': len(calculator.get_feature_list()),
        'features_created': calculator.get_feature_list()
    }
    
    logger.info(f"  ✓ Shape: {df_clean.shape} → {df_features.shape}")
    logger.info(f"  ✓ Features created: {len(calculator.get_feature_list())}")
    
    return summary


def engineer_economic_features():
    """
    Engineer features from economic indicators
    Creates derived features and lags
    """
    logger.info("=" * 70)
    logger.info("ENGINEERING ECONOMIC FEATURES")
    logger.info("=" * 70)
    
    # Load cleaned economic data
    input_path = PROCESSED_DATA_DIR / 'economic_indicators_clean.parquet'
    
    if not input_path.exists():
        logger.warning("Economic data not found")
        return None
    
    df = pd.read_parquet(input_path)
    logger.info(f"Loaded {len(df):,} records")
    
    # Pivot data so each series is a column
    df_pivot = df.pivot(index='date', columns='series_id', values='value')
    df_pivot = df_pivot.sort_index()
    
    logger.info(f"Pivoted shape: {df_pivot.shape}")
    
    # Create derived features
    features_created = []
    
    # 1. Rate changes (first difference)
    for col in df_pivot.columns:
        df_pivot[f'{col}_change'] = df_pivot[col].diff()
        features_created.append(f'{col}_change')
    
    # 2. Percentage changes
    for col in df_pivot.columns:
        if not col.endswith('_change'):
            df_pivot[f'{col}_pct_change'] = df_pivot[col].pct_change() * 100
            features_created.append(f'{col}_pct_change')
    
    # 3. Moving averages (for smoothing)
    for col in ['FEDFUNDS', 'CPIAUCSL', 'UNRATE']:
        if col in df_pivot.columns:
            for window in [3, 6, 12]:  # Monthly data: 3, 6, 12 months
                df_pivot[f'{col}_ma{window}'] = df_pivot[col].rolling(window=window).mean()
                features_created.append(f'{col}_ma{window}')
    
    # 4. Lagged features (for time series modeling)
    for col in ['FEDFUNDS', 'CPIAUCSL', 'UNRATE']:
        if col in df_pivot.columns:
            for lag in [1, 3, 6, 12]:
                df_pivot[f'{col}_lag{lag}'] = df_pivot[col].shift(lag)
                features_created.append(f'{col}_lag{lag}')
    
    # 5. Interest rate differentials (important for forex)
    if 'FEDFUNDS' in df_pivot.columns:
        # Assume other central bank rates would be here
        # For now, create relative features
        df_pivot['FEDFUNDS_zscore'] = (df_pivot['FEDFUNDS'] - df_pivot['FEDFUNDS'].mean()) / df_pivot['FEDFUNDS'].std()
        features_created.append('FEDFUNDS_zscore')
    
    # Drop rows with NaN from feature calculations
    original_rows = len(df_pivot)
    df_pivot = df_pivot.dropna()
    rows_removed = original_rows - len(df_pivot)
    
    logger.info(f"Removed {rows_removed} rows with NaN from feature calculations")
    
    # Reset index to make date a column
    df_pivot = df_pivot.reset_index()
    
    # Save feature-engineered economic data
    output_path = PROCESSED_DATA_DIR / 'economic_indicators_features.parquet'
    df_pivot.to_parquet(output_path, index=False)
    logger.info(f"✓ Saved: {output_path}")
    
    # Save as CSV too
    csv_path = PROCESSED_DATA_DIR / 'economic_indicators_features.csv'
    df_pivot.to_csv(csv_path, index=False)
    logger.info(f"✓ Saved CSV: {csv_path}")
    
    # Save feature list
    feature_list_path = OUTPUT_DIR / 'features_economic.txt'
    with open(feature_list_path, 'w') as f:
        f.write("Economic Indicator Features\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Total Features: {len(features_created)}\n\n")
        for i, feat in enumerate(features_created, 1):
            f.write(f"{i:3d}. {feat}\n")
    
    logger.info(f"✓ Saved feature list: {feature_list_path}")
    
    # Summary
    summary = {
        'input_rows': len(df),
        'output_rows': len(df_pivot),
        'total_columns': len(df_pivot.columns),
        'features_created': len(features_created),
        'feature_list': features_created
    }
    
    logger.info(f"✓ Created {len(features_created)} economic features")
    logger.info(f"✓ Final shape: {df_pivot.shape}")
    
    return summary


def create_feature_summary():
    """Create comprehensive feature summary document"""
    logger.info("=" * 70)
    logger.info("CREATING FEATURE SUMMARY")
    logger.info("=" * 70)
    
    summary_path = OUTPUT_DIR / 'feature_engineering_summary.txt'
    
    with open(summary_path, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("FOREX ALPHA - FEATURE ENGINEERING SUMMARY\n")
        f.write("=" * 70 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 70 + "\n\n")
        
        f.write("FEATURE CATEGORIES:\n\n")
        
        f.write("1. PRICE-BASED FEATURES\n")
        f.write("   - Returns (1d, 5d, 10d, 20d)\n")
        f.write("   - Log returns (1d, 5d, 10d, 20d)\n")
        f.write("   - Volatility (5d, 10d, 20d windows)\n\n")
        
        f.write("2. MOVING AVERAGES\n")
        f.write("   - SMA (7, 14, 21, 50, 100, 200)\n")
        f.write("   - EMA (7, 14, 21, 50, 100, 200)\n")
        f.write("   - Price-to-MA ratios\n\n")
        
        f.write("3. MOMENTUM INDICATORS\n")
        f.write("   - RSI (14-period)\n")
        f.write("   - MACD (12/26/9)\n")
        f.write("   - Stochastic Oscillator (14-period)\n\n")
        
        f.write("4. VOLATILITY INDICATORS\n")
        f.write("   - Bollinger Bands (20-period, 2-std)\n")
        f.write("   - ATR (14-period)\n")
        f.write("   - Bandwidth and %B\n\n")
        
        f.write("5. PATTERN FEATURES\n")
        f.write("   - Candlestick patterns (Doji, etc.)\n")
        f.write("   - Bullish/Bearish indicators\n")
        f.write("   - Gap detection\n\n")
        
        f.write("6. TIME FEATURES\n")
        f.write("   - Year, Month, Day, Hour\n")
        f.write("   - Day of week\n")
        f.write("   - Trading session indicators\n")
        f.write("   - Cyclical encodings (sin/cos)\n\n")
        
        f.write("7. ECONOMIC FEATURES\n")
        f.write("   - Rate changes and % changes\n")
        f.write("   - Moving averages (3, 6, 12 months)\n")
        f.write("   - Lagged features (1, 3, 6, 12 months)\n")
        f.write("   - Z-scores\n\n")
        
        f.write("=" * 70 + "\n")
        f.write("FEATURE ENGINEERING BEST PRACTICES APPLIED:\n")
        f.write("=" * 70 + "\n\n")
        f.write("✓ Removed NaN values from indicator calculations\n")
        f.write("✓ Created both raw and normalized features\n")
        f.write("✓ Added lagged features for time series modeling\n")
        f.write("✓ Implemented cyclical encoding for time features\n")
        f.write("✓ Calculated both absolute and relative indicators\n")
        f.write("✓ Generated cross-indicator features\n\n")
        
        f.write("=" * 70 + "\n")
        f.write("NEXT STEPS:\n")
        f.write("=" * 70 + "\n\n")
        f.write("1. Feature selection using correlation analysis\n")
        f.write("2. Feature importance analysis\n")
        f.write("3. Dimensionality reduction (PCA if needed)\n")
        f.write("4. Feature scaling/normalization for ML models\n")
        f.write("5. Train-test-validation split\n\n")
    
    logger.info(f"✓ Saved feature summary: {summary_path}")


def main():
    """Main feature engineering execution"""
    print("\n" + "=" * 70)
    print("  FOREX ALPHA - FEATURE ENGINEERING PIPELINE")
    print("=" * 70)
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")
    
    engineering_report = {
        'timestamp': datetime.now().isoformat(),
        'results': {}
    }
    
    try:
        # Engineer economic features
        eco_summary = engineer_economic_features()
        if eco_summary:
            engineering_report['results']['economic_indicators'] = eco_summary
        
        # Engineer OHLC features for each currency pair
        from config import CURRENCY_PAIRS
        
        ohlc_summaries = []
        logger.info("=" * 70)
        logger.info("ENGINEERING OHLC FEATURES")
        logger.info("=" * 70)
        
        for symbol in CURRENCY_PAIRS:
            summary = engineer_ohlc_features(symbol, '1D')
            if summary:
                ohlc_summaries.append(summary)
        
        if ohlc_summaries:
            engineering_report['results']['ohlc_data'] = ohlc_summaries
        
        # Create feature summary document
        create_feature_summary()
        
        # Save engineering report
        report_path = OUTPUT_DIR / 'feature_engineering_report.json'
        with open(report_path, 'w') as f:
            json.dump(engineering_report, f, indent=2, default=str)
        
        logger.info(f"\n✓ Saved engineering report: {report_path}")
        
        # Print summary
        print("\n" + "=" * 70)
        print("  FEATURE ENGINEERING SUMMARY")
        print("=" * 70)
        
        if 'economic_indicators' in engineering_report['results']:
            eco = engineering_report['results']['economic_indicators']
            print(f"\n📊 Economic Indicators:")
            print(f"   Features created: {eco['features_created']}")
            print(f"   Final shape: ({eco['output_rows']}, {eco['total_columns']})")
        
        if 'ohlc_data' in engineering_report['results']:
            print(f"\n💹 OHLC Price Data:")
            for summary in engineering_report['results']['ohlc_data']:
                print(f"   {summary['symbol']}: {summary['feature_columns']} features")
                print(f"   Shape: ({summary['output_rows']}, {summary['total_columns']})")
        
        print("\n" + "=" * 70)
        
        logger.info("\n✓ FEATURE ENGINEERING COMPLETED SUCCESSFULLY")
        
    except Exception as e:
        logger.error(f"✗ Error during feature engineering: {e}")
        raise
    
    print("\n" + "=" * 70)
    print("  ENGINEERING COMPLETE - Check processed_data/ folder")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    main()
