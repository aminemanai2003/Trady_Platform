"""
01_explore_data.py
Exploratory Data Analysis (EDA) for Forex Alpha Data
Analyzes all available data sources and generates comprehensive reports
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys
import json
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config import POSTGRES_CONFIG, INFLUXDB_CONFIG, OUTPUT_DIR, CURRENCY_PAIRS
from utils import DataLoader
from loguru import logger

# Configure plotting
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Configure logger
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")
logger.add(OUTPUT_DIR / "eda.log", rotation="10 MB")


def explore_economic_data(loader: DataLoader):
    """Explore economic indicators data"""
    logger.info("=" * 70)
    logger.info("EXPLORING ECONOMIC INDICATORS DATA")
    logger.info("=" * 70)
    
    # Load all economic data
    df = loader.load_economic_indicators()
    
    if len(df) == 0:
        logger.warning("No economic data found")
        return None
    
    print(f"\n📊 Economic Indicators Dataset")
    print("=" * 70)
    print(f"Total Records: {len(df):,}")
    print(f"Date Range: {df['date'].min()} to {df['date'].max()}")
    print(f"Unique Series: {df['series_id'].nunique()}")
    print("\nColumns:", list(df.columns))
    print("\nData Types:")
    print(df.dtypes)
    
    # Stats by series
    print("\n\n📈 Statistics by Series:")
    print("=" * 70)
    series_stats = df.groupby('series_id').agg({
        'value': ['count', 'mean', 'std', 'min', 'max'],
        'date': ['min', 'max']
    }).round(2)
    print(series_stats)
    
    # Missing values
    print("\n\n🔍 Missing Values:")
    print("=" * 70)
    missing = df.isnull().sum()
    if missing.sum() > 0:
        print(missing[missing > 0])
    else:
        print("✓ No missing values found")
    
    # Visualizations
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Economic Indicators - Exploratory Analysis', fontsize=16, fontweight='bold')
    
    # 1. Records per series
    series_counts = df['series_id'].value_counts()
    axes[0, 0].barh(series_counts.index, series_counts.values)
    axes[0, 0].set_xlabel('Number of Records')
    axes[0, 0].set_title('Records per Economic Series')
    axes[0, 0].grid(True, alpha=0.3)
    
    # 2. Time coverage
    df['year'] = pd.to_datetime(df['date']).dt.year
    year_counts = df['year'].value_counts().sort_index()
    axes[0, 1].bar(year_counts.index, year_counts.values)
    axes[0, 1].set_xlabel('Year')
    axes[0, 1].set_ylabel('Number of Records')
    axes[0, 1].set_title('Data Coverage by Year')
    axes[0, 1].grid(True, alpha=0.3)
    
    # 3. Value distributions (sample series)
    sample_series = df['series_id'].unique()[:4]
    for i, series_id in enumerate(sample_series):
        series_data = df[df['series_id'] == series_id]['value']
        axes[1, 0].hist(series_data, alpha=0.5, label=series_id, bins=20)
    axes[1, 0].set_xlabel('Value')
    axes[1, 0].set_ylabel('Frequency')
    axes[1, 0].set_title('Value Distributions (Sample Series)')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # 4. Time series plot (key series)
    key_series = ['FEDFUNDS', 'CPIAUCSL', 'UNRATE']
    for series_id in key_series:
        if series_id in df['series_id'].values:
            series_df = df[df['series_id'] == series_id].sort_values('date')
            axes[1, 1].plot(pd.to_datetime(series_df['date']), series_df['value'], 
                          label=series_id, marker='o', markersize=2)
    axes[1, 1].set_xlabel('Date')
    axes[1, 1].set_ylabel('Value')
    axes[1, 1].set_title('Key Economic Indicators Over Time')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    axes[1, 1].tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plot_path = OUTPUT_DIR / 'eda_economic_indicators.png'
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    logger.info(f"✓ Saved plot: {plot_path}")
    plt.close()
    
    # Statistical summary
    summary = {
        'total_records': len(df),
        'unique_series': df['series_id'].nunique(),
        'date_range': {
            'min': str(df['date'].min()),
            'max': str(df['date'].max())
        },
        'series_list': df['series_id'].unique().tolist(),
        'series_stats': {
            series_id: {
                'count': int(group['value'].count()),
                'mean': float(group['value'].mean()),
                'std': float(group['value'].std()),
                'min': float(group['value'].min()),
                'max': float(group['value'].max())
            }
            for series_id, group in df.groupby('series_id')
        }
    }
    
    return summary


def explore_news_data(loader: DataLoader):
    """Explore news articles data"""
    logger.info("=" * 70)
    logger.info("EXPLORING NEWS ARTICLES DATA")
    logger.info("=" * 70)
    
    # Load all news data
    df = loader.load_news_articles()
    
    if len(df) == 0:
        logger.warning("No news data found")
        return None
    
    print(f"\n📰 News Articles Dataset")
    print("=" * 70)
    print(f"Total Articles: {len(df):,}")
    print(f"Date Range: {df['published_at'].min()} to {df['published_at'].max()}")
    print(f"Unique Sources: {df['source'].nunique()}")
    print("\nColumns:", list(df.columns))
    
    # Stats by source
    print("\n\n📊 Articles by Source:")
    print("=" * 70)
    source_counts = df['source'].value_counts()
    print(source_counts)
    
    # Recent articles
    print("\n\n📄 Recent Articles (Sample):")
    print("=" * 70)
    recent = df.nlargest(5, 'published_at')[['title', 'source', 'published_at']]
    for idx, row in recent.iterrows():
        print(f"\n• [{row['source']}] {row['title']}")
        print(f"  Published: {row['published_at']}")
    
    # Visualizations
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('News Articles - Exploratory Analysis', fontsize=16, fontweight='bold')
    
    # 1. Articles per source
    source_counts.plot(kind='barh', ax=axes[0])
    axes[0].set_xlabel('Number of Articles')
    axes[0].set_title('Articles by Source')
    axes[0].grid(True, alpha=0.3)
    
    # 2. Articles over time
    df['date'] = pd.to_datetime(df['published_at']).dt.date
    date_counts = df['date'].value_counts().sort_index()
    axes[1].plot(date_counts.index, date_counts.values, marker='o')
    axes[1].set_xlabel('Date')
    axes[1].set_ylabel('Number of Articles')
    axes[1].set_title('Articles Published Over Time')
    axes[1].grid(True, alpha=0.3)
    axes[1].tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plot_path = OUTPUT_DIR / 'eda_news_articles.png'
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    logger.info(f"✓ Saved plot: {plot_path}")
    plt.close()
    
    summary = {
        'total_articles': len(df),
        'unique_sources': df['source'].nunique(),
        'sources': df['source'].unique().tolist(),
        'date_range': {
            'min': str(df['published_at'].min()),
            'max': str(df['published_at'].max())
        },
        'articles_by_source': df['source'].value_counts().to_dict()
    }
    
    return summary


def explore_ohlc_data(loader: DataLoader):
    """Explore OHLC price data"""
    logger.info("=" * 70)
    logger.info("EXPLORING OHLC PRICE DATA")
    logger.info("=" * 70)
    
    all_summaries = {}
    
    # Try to load data for each currency pair
    for symbol in CURRENCY_PAIRS:
        logger.info(f"\nLoading {symbol}...")
        df = loader.load_ohlc_data(symbol, '1D', days_back=365*2)
        
        if len(df) == 0:
            logger.warning(f"  ⚠ No data found for {symbol}")
            continue
        
        print(f"\n💹 {symbol} Dataset")
        print("=" * 70)
        print(f"Total Candles: {len(df):,}")
        print(f"Date Range: {df['time'].min()} to {df['time'].max()}")
        print(f"Price Range: {df['close'].min():.5f} - {df['close'].max():.5f}")
        
        all_summaries[symbol] = {
            'total_candles': len(df),
            'date_range': {
                'min': str(df['time'].min()),
                'max': str(df['time'].max())
            },
            'price_stats': {
                'min': float(df['close'].min()),
                'max': float(df['close'].max()),
                'mean': float(df['close'].mean()),
                'std': float(df['close'].std())
            }
        }
    
    if not all_summaries:
        logger.warning("No OHLC data available")
        return None
    
    return all_summaries


def generate_summary_report(economic_summary, news_summary, ohlc_summary):
    """Generate comprehensive summary report"""
    logger.info("=" * 70)
    logger.info("GENERATING SUMMARY REPORT")
    logger.info("=" * 70)
    
    report = {
        'generated_at': datetime.now().isoformat(),
        'data_sources': {}
    }
    
    if economic_summary:
        report['data_sources']['economic_indicators'] = economic_summary
    
    if news_summary:
        report['data_sources']['news_articles'] = news_summary
    
    if ohlc_summary:
        report['data_sources']['ohlc_prices'] = ohlc_summary
    
    # Save JSON report
    report_path = OUTPUT_DIR / 'eda_summary_report.json'
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"✓ Saved summary report: {report_path}")
    
    # Print summary
    print("\n\n" + "=" * 70)
    print("  DATA EXPLORATION SUMMARY")
    print("=" * 70)
    
    if economic_summary:
        print(f"\n📊 Economic Indicators: {economic_summary['total_records']:,} records")
        print(f"   Series: {economic_summary['unique_series']}")
    
    if news_summary:
        print(f"\n📰 News Articles: {news_summary['total_articles']:,} articles")
        print(f"   Sources: {news_summary['unique_sources']}")
    
    if ohlc_summary:
        print(f"\n💹 OHLC Price Data: {len(ohlc_summary)} currency pairs")
        for symbol, stats in ohlc_summary.items():
            print(f"   {symbol}: {stats['total_candles']:,} candles")
    
    print("\n" + "=" * 70)
    
    return report


def main():
    """Main EDA execution"""
    print("\n" + "=" * 70)
    print("  FOREX ALPHA - EXPLORATORY DATA ANALYSIS")
    print("=" * 70)
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")
    
    # Initialize data loader
    loader = DataLoader(POSTGRES_CONFIG, INFLUXDB_CONFIG)
    
    try:
        # Explore each data source
        economic_summary = explore_economic_data(loader)
        news_summary = explore_news_data(loader)
        ohlc_summary = explore_ohlc_data(loader)
        
        # Generate comprehensive report
        report = generate_summary_report(economic_summary, news_summary, ohlc_summary)
        
        logger.info("\n✓ EXPLORATORY DATA ANALYSIS COMPLETED SUCCESSFULLY")
        
    except Exception as e:
        logger.error(f"✗ Error during EDA: {e}")
        raise
    
    finally:
        loader.close()
    
    print("\n" + "=" * 70)
    print("  EDA COMPLETE - Check output/ folder for results")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    main()
