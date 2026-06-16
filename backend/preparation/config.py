"""
Configuration Management for Data Preparation
Centralized configuration for all data preparation scripts
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base Paths
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
RAW_DATA_DIR = BASE_DIR / "raw_data"
PROCESSED_DATA_DIR = BASE_DIR / "processed_data"

# Create directories if they don't exist
OUTPUT_DIR.mkdir(exist_ok=True)
RAW_DATA_DIR.mkdir(exist_ok=True)
PROCESSED_DATA_DIR.mkdir(exist_ok=True)

# Database Configuration
POSTGRES_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'forex_metadata'),
    'user': os.getenv('POSTGRES_USER', 'forex_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'forex_pass_2026')
}

INFLUXDB_CONFIG = {
    'url': os.getenv('INFLUXDB_URL', 'http://localhost:8086'),
    'token': os.getenv('INFLUXDB_TOKEN', 'my-super-secret-token'),
    'org': os.getenv('INFLUXDB_ORG', 'forexalpha'),
    'bucket': os.getenv('INFLUXDB_BUCKET', 'forex_data')
}

# Currency Pairs
CURRENCY_PAIRS = ['EURUSD', 'USDJPY', 'GBPUSD', 'USDCHF']

# Timeframes
TIMEFRAMES = ['1H', '4H', '1D', '1W', '1M']

# Feature Engineering Configuration
FEATURE_CONFIG = {
    'lookback_periods': [5, 10, 20, 50, 100, 200],
    'moving_averages': [7, 14, 21, 50, 100, 200],
    'rsi_periods': [14],
    'macd': {
        'fast': 12,
        'slow': 26,
        'signal': 9
    },
    'bollinger': {
        'period': 20,
        'std': 2
    },
    'atr_period': 14
}

# Validation Thresholds
VALIDATION_CONFIG = {
    'min_data_points': int(os.getenv('MIN_DATA_POINTS', 1000)),
    'max_missing_ratio': float(os.getenv('MAX_MISSING_RATIO', 0.05)),
    'outlier_std_threshold': float(os.getenv('OUTLIER_STD_THRESHOLD', 3)),
    'min_date': '2020-01-01',
    'max_date': '2026-12-31'
}

# Economic Indicators (FRED)
FRED_INDICATORS = [
    'CPIAUCSL',      # US CPI
    'UNRATE',        # Unemployment Rate
    'FEDFUNDS',      # Federal Funds Rate
    'GDP',           # US GDP
    'DEXUSEU',       # EUR/USD Exchange Rate
    'DEXJPUS',       # USD/JPY Exchange Rate
    'DEXUSUK',       # GBP/USD Exchange Rate
    'DEXSZUS',       # USD/CHF Exchange Rate
    'DGS10',         # US 10Y Treasury
    'T10YIE',        # US 10Y Inflation Expectations
]

# Logging Configuration
LOG_CONFIG = {
    'level': 'INFO',
    'format': '<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>',
    'log_file': OUTPUT_DIR / 'data_preparation.log'
}

def get_postgres_connection_string():
    """Get PostgreSQL connection string"""
    return f"postgresql://{POSTGRES_CONFIG['user']}:{POSTGRES_CONFIG['password']}@{POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['database']}"

def get_postgres_dict_connection():
    """Get PostgreSQL connection as dictionary"""
    return POSTGRES_CONFIG.copy()

if __name__ == '__main__':
    print("=" * 60)
    print("DATA PREPARATION CONFIGURATION")
    print("=" * 60)
    print(f"\nBase Directory: {BASE_DIR}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print(f"\nPostgreSQL: {POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['database']}")
    print(f"InfluxDB: {INFLUXDB_CONFIG['url']}")
    print(f"\nCurrency Pairs: {', '.join(CURRENCY_PAIRS)}")
    print(f"Timeframes: {', '.join(TIMEFRAMES)}")
    print(f"Feature Config: {len(FEATURE_CONFIG['moving_averages'])} moving averages")
    print("=" * 60)
