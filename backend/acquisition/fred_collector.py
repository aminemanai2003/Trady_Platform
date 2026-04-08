"""
FRED Data Acquisition Script
Collects macroeconomic indicators from FRED API and stores in PostgreSQL
"""

from fredapi import Fred
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Configuration
FRED_API_KEY = os.getenv('FRED_API_KEY')
POSTGRES_HOST = os.getenv('POSTGRES_HOST')
POSTGRES_PORT = os.getenv('POSTGRES_PORT')
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')

# Economic indicators to fetch
INDICATORS = {
    'CPIAUCSL': 'US CPI',
    'UNRATE': 'US Unemployment Rate',
    'FEDFUNDS': 'Federal Funds Rate',
    'GDP': 'US GDP',
    'DEXUSEU': 'EUR/USD Exchange Rate',
    'DEXJPUS': 'USD/JPY Exchange Rate',
    'DEXUSUK': 'GBP/USD Exchange Rate',
    'DEXSZUS': 'USD/CHF Exchange Rate',
    'DGS10': 'US 10Y Treasury',
    'T10YIE': 'US 10Y Inflation Expectations',
}

def fetch_fred_data():
    """Fetch all economic indicators from FRED"""
    print("=" * 60)
    print("FRED DATA ACQUISITION")
    print("=" * 60)
    
    fred = Fred(api_key=FRED_API_KEY)
    all_data = []
    
    for series_id, name in INDICATORS.items():
        print(f"\n📊 Fetching {name} ({series_id})...")
        
        try:
            # Fetch last 10 years
            data = fred.get_series(series_id, observation_start='2015-01-01')
            
            # Convert to DataFrame
            df = pd.DataFrame({
                'date': data.index,
                'value': data.values,
                'series_id': series_id,
                'indicator_name': name
            })
            
            print(f"   ✅ Retrieved {len(df):,} observations")
            print(f"   📅 From {df['date'].min()} to {df['date'].max()}")
            
            all_data.append(df)
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Combine all data
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        print(f"\n✅ Total observations: {len(combined):,}")
        return combined
    
    return None

def write_to_postgres(df):
    """Write data to PostgreSQL"""
    print("\n💾 Writing to PostgreSQL...")
    
    conn_string = f"host={POSTGRES_HOST} port={POSTGRES_PORT} dbname={POSTGRES_DB} user={POSTGRES_USER} password={POSTGRES_PASSWORD}"
    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor()
    
    try:
        # Prepare data
        values = [
            (row['date'], row['series_id'], row['indicator_name'], row['value'])
            for _, row in df.iterrows()
        ]

        # Prefer current schema and gracefully fallback to legacy table.
        try:
            execute_values(
                cursor,
                """
                INSERT INTO macro_indicators (date, series_id, indicator_name, value)
                VALUES %s
                ON CONFLICT (date, series_id) DO UPDATE
                SET value = EXCLUDED.value
                """,
                values
            )
        except Exception:
            conn.rollback()
            execute_values(
                cursor,
                """
                INSERT INTO economic_indicators (date, series_id, indicator_name, value)
                VALUES %s
                ON CONFLICT (date, series_id) DO UPDATE
                SET value = EXCLUDED.value
                """,
                values
            )
        
        conn.commit()
        print(f"✅ Wrote {len(values):,} records to PostgreSQL")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Write failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def main():
    # Fetch data
    df = fetch_fred_data()
    
    if df is not None and len(df) > 0:
        # Write to database
        write_to_postgres(df)
        
        print("\n" + "=" * 60)
        print("✅ FRED DATA ACQUISITION COMPLETE")
        print("=" * 60)
    else:
        print("\n❌ No data collected")

if __name__ == "__main__":
    main()
    
