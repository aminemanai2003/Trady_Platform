"""
02_clean_data.py
Data Cleaning Pipeline for Forex Alpha Data
Cleans and preprocesses all data sources
"""

import pandas as pd
import sys
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config import POSTGRES_CONFIG, INFLUXDB_CONFIG, OUTPUT_DIR, PROCESSED_DATA_DIR
from utils import DataLoader, DataCleaner
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")
logger.add(OUTPUT_DIR / "cleaning.log", rotation="10 MB")


def clean_economic_indicators(loader: DataLoader, cleaner: DataCleaner):
    """Clean economic indicators data"""
    logger.info("=" * 70)
    logger.info("CLEANING ECONOMIC INDICATORS")
    logger.info("=" * 70)
    
    # Load raw data
    df_raw = loader.load_economic_indicators()
    
    if len(df_raw) == 0:
        logger.warning("No economic data to clean")
        return None
    
    logger.info(f"Loaded {len(df_raw):,} raw records")
    
    # Clean the data
    df_clean = cleaner.clean_economic_data(df_raw)
    
    # Convert date to datetime
    df_clean['date'] = pd.to_datetime(df_clean['date'])
    
    # Sort by date and series
    df_clean = df_clean.sort_values(['series_id', 'date']).reset_index(drop=True)
    
    # Save cleaned data
    output_path = PROCESSED_DATA_DIR / 'economic_indicators_clean.parquet'
    df_clean.to_parquet(output_path, index=False)
    logger.info(f"✓ Saved cleaned data: {output_path}")
    
    # Also save as CSV for easy viewing
    csv_path = PROCESSED_DATA_DIR / 'economic_indicators_clean.csv'
    df_clean.to_csv(csv_path, index=False)
    logger.info(f"✓ Saved CSV copy: {csv_path}")
    
    # Cleaning summary
    summary = {
        'raw_records': len(df_raw),
        'cleaned_records': len(df_clean),
        'records_removed': len(df_raw) - len(df_clean),
        'removal_ratio': f"{((len(df_raw) - len(df_clean)) / len(df_raw) * 100):.2f}%",
        'unique_series': df_clean['series_id'].nunique(),
        'date_range': {
            'min': str(df_clean['date'].min()),
            'max': str(df_clean['date'].max())
        }
    }
    
    logger.info(f"\nCleaning Summary:")
    logger.info(f"  Raw records: {summary['raw_records']:,}")
    logger.info(f"  Clean records: {summary['cleaned_records']:,}")
    logger.info(f"  Removed: {summary['records_removed']:,} ({summary['removal_ratio']})")
    
    return summary


def clean_news_articles(loader: DataLoader, cleaner: DataCleaner):
    """Clean news articles data"""
    logger.info("=" * 70)
    logger.info("CLEANING NEWS ARTICLES")
    logger.info("=" * 70)
    
    # Load raw data
    df_raw = loader.load_news_articles()
    
    if len(df_raw) == 0:
        logger.warning("No news data to clean")
        return None
    
    logger.info(f"Loaded {len(df_raw):,} raw articles")
    
    # Basic cleaning
    df_clean = df_raw.copy()
    
    # Remove duplicates based on URL
    df_clean = cleaner.remove_duplicates(df_clean, subset=['url'])
    
    # Remove rows with missing critical fields
    df_clean = df_clean.dropna(subset=['title', 'url'])
    
    # Convert dates
    df_clean['published_at'] = pd.to_datetime(df_clean['published_at'])
    df_clean['scraped_at'] = pd.to_datetime(df_clean['scraped_at'])
    
    # Clean text fields
    df_clean['title'] = df_clean['title'].str.strip()
    df_clean['content'] = df_clean['content'].fillna('').str.strip()
    
    # Sort by published date
    df_clean = df_clean.sort_values('published_at', ascending=False).reset_index(drop=True)
    
    # Save cleaned data
    output_path = PROCESSED_DATA_DIR / 'news_articles_clean.parquet'
    df_clean.to_parquet(output_path, index=False)
    logger.info(f"✓ Saved cleaned data: {output_path}")
    
    csv_path = PROCESSED_DATA_DIR / 'news_articles_clean.csv'
    df_clean.to_csv(csv_path, index=False)
    logger.info(f"✓ Saved CSV copy: {csv_path}")
    
    # Cleaning summary
    summary = {
        'raw_articles': len(df_raw),
        'cleaned_articles': len(df_clean),
        'articles_removed': len(df_raw) - len(df_clean),
        'removal_ratio': f"{((len(df_raw) - len(df_clean)) / len(df_raw) * 100):.2f}%",
        'unique_sources': df_clean['source'].nunique(),
        'date_range': {
            'min': str(df_clean['published_at'].min()),
            'max': str(df_clean['published_at'].max())
        }
    }
    
    logger.info(f"\nCleaning Summary:")
    logger.info(f"  Raw articles: {summary['raw_articles']:,}")
    logger.info(f"  Clean articles: {summary['cleaned_articles']:,}")
    logger.info(f"  Removed: {summary['articles_removed']:,} ({summary['removal_ratio']})")
    
    return summary


def clean_ohlc_data(loader: DataLoader, cleaner: DataCleaner, symbol: str, timeframe: str = '1D'):
    """Clean OHLC price data for a specific symbol"""
    logger.info(f"Cleaning {symbol} {timeframe}...")
    
    # Load raw data
    df_raw = loader.load_ohlc_data(symbol, timeframe, days_back=365*2)
    
    if len(df_raw) == 0:
        logger.warning(f"  ⚠ No data found for {symbol} {timeframe}")
        return None
    
    logger.info(f"  Loaded {len(df_raw):,} raw candles")
    
    # Clean the data
    df_clean = cleaner.clean_ohlc_data(df_raw)
    
    # Ensure proper sorting
    df_clean = df_clean.sort_values('time').reset_index(drop=True)
    
    # Save cleaned data
    filename = f'ohlc_{symbol}_{timeframe}_clean.parquet'
    output_path = PROCESSED_DATA_DIR / filename
    df_clean.to_parquet(output_path, index=False)
    logger.info(f"  ✓ Saved: {output_path}")
    
    # Summary
    summary = {
        'symbol': symbol,
        'timeframe': timeframe,
        'raw_candles': len(df_raw),
        'cleaned_candles': len(df_clean),
        'candles_removed': len(df_raw) - len(df_clean),
        'date_range': {
            'min': str(df_clean['time'].min()),
            'max': str(df_clean['time'].max())
        },
        'price_range': {
            'min': float(df_clean['close'].min()),
            'max': float(df_clean['close'].max())
        }
    }
    
    return summary


def main():
    """Main cleaning execution"""
    print("\n" + "=" * 70)
    print("  FOREX ALPHA - DATA CLEANING PIPELINE")
    print("=" * 70)
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")
    
    # Initialize
    loader = DataLoader(POSTGRES_CONFIG, INFLUXDB_CONFIG)
    cleaner = DataCleaner(outlier_std_threshold=3.0, max_missing_ratio=0.05)
    
    cleaning_report = {
        'timestamp': datetime.now().isoformat(),
        'results': {}
    }
    
    try:
        # Clean economic indicators
        eco_summary = clean_economic_indicators(loader, cleaner)
        if eco_summary:
            cleaning_report['results']['economic_indicators'] = eco_summary
        
        # Clean news articles
        news_summary = clean_news_articles(loader, cleaner)
        if news_summary:
            cleaning_report['results']['news_articles'] = news_summary
        
        # Clean OHLC data for each currency pair
        from config import CURRENCY_PAIRS, TIMEFRAMES
        
        ohlc_summaries = []
        logger.info("=" * 70)
        logger.info("CLEANING OHLC PRICE DATA")
        logger.info("=" * 70)
        
        for symbol in CURRENCY_PAIRS:
            for timeframe in ['1D']:  # Start with daily data
                summary = clean_ohlc_data(loader, cleaner, symbol, timeframe)
                if summary:
                    ohlc_summaries.append(summary)
        
        if ohlc_summaries:
            cleaning_report['results']['ohlc_data'] = ohlc_summaries
        
        # Save cleaning report
        report_path = OUTPUT_DIR / 'cleaning_report.json'
        with open(report_path, 'w') as f:
            json.dump(cleaning_report, f, indent=2)
        
        logger.info(f"\n✓ Saved cleaning report: {report_path}")
        
        # Print summary
        print("\n" + "=" * 70)
        print("  DATA CLEANING SUMMARY")
        print("=" * 70)
        
        if 'economic_indicators' in cleaning_report['results']:
            eco = cleaning_report['results']['economic_indicators']
            print(f"\n📊 Economic Indicators:")
            print(f"   Cleaned: {eco['cleaned_records']:,} records")
            print(f"   Removed: {eco['records_removed']:,} ({eco['removal_ratio']})")
        
        if 'news_articles' in cleaning_report['results']:
            news = cleaning_report['results']['news_articles']
            print(f"\n📰 News Articles:")
            print(f"   Cleaned: {news['cleaned_articles']:,} articles")
            print(f"   Removed: {news['articles_removed']:,} ({news['removal_ratio']})")
        
        if 'ohlc_data' in cleaning_report['results']:
            print(f"\n💹 OHLC Price Data:")
            for summary in cleaning_report['results']['ohlc_data']:
                print(f"   {summary['symbol']} {summary['timeframe']}: {summary['cleaned_candles']:,} candles")
        
        print("\n" + "=" * 70)
        
        logger.info("\n✓ DATA CLEANING COMPLETED SUCCESSFULLY")
        
    except Exception as e:
        logger.error(f"✗ Error during cleaning: {e}")
        raise
    
    finally:
        loader.close()
    
    print("\n" + "=" * 70)
    print("  CLEANING COMPLETE - Check processed_data/ folder")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    main()
