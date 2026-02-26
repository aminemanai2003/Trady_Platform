"""
MT5 Data Acquisition Script
Collects historical OHLC price data from MetaTrader 5 and stores in InfluxDB
"""

import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pandas as pd
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
MT5_LOGIN_STR = os.getenv('MT5_LOGIN')
# Try to convert to int if it's numeric, otherwise use as string
try:
    MT5_LOGIN = int(MT5_LOGIN_STR)
except (ValueError, TypeError):
    MT5_LOGIN = MT5_LOGIN_STR
MT5_PASSWORD = os.getenv('MT5_PASSWORD')
MT5_SERVER = os.getenv('MT5_SERVER')

INFLUXDB_URL = os.getenv('INFLUXDB_URL')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET')

# Currency pairs
PAIRS = ['EURUSD', 'USDJPY', 'GBPUSD', 'USDCHF']
TIMEFRAMES = {
    '1H': mt5.TIMEFRAME_H1,
    '4H': mt5.TIMEFRAME_H4,
    '1D': mt5.TIMEFRAME_D1,
}

def connect_mt5():
    """Connect to MT5 terminal"""
    if not mt5.initialize():
        print(f"❌ MT5 initialize failed: {mt5.last_error()}")
        return False
    
    if not mt5.login(MT5_LOGIN, MT5_PASSWORD, MT5_SERVER):
        print(f"❌ MT5 login failed: {mt5.last_error()}")
        return False
    
    print(f"✅ Connected to MT5: {MT5_SERVER}")
    print(f"   Account: {mt5.account_info().login}")
    return True

def get_historical_data(symbol, timeframe_name, timeframe_mt5, days_back=365*5):
    """Get historical OHLC data"""
    print(f"\n📊 Fetching {symbol} {timeframe_name} data...")
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    # Fetch data
    rates = mt5.copy_rates_range(symbol, timeframe_mt5, start_date, end_date)
    
    if rates is None or len(rates) == 0:
        print(f"   ❌ No data: {mt5.last_error()}")
        return None
    
    # Convert to DataFrame
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    print(f"   ✅ Retrieved {len(df):,} candles")
    print(f"   📅 From {df['time'].min()} to {df['time'].max()}")
    
    return df

def write_to_influxdb(df, symbol, timeframe):
    """Write data to InfluxDB"""
    print(f"   💾 Writing to InfluxDB...")
    
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    
    points = []
    for _, row in df.iterrows():
        point = (
            Point("forex_prices")
            .tag("symbol", symbol)
            .tag("timeframe", timeframe)
            .field("open", float(row['open']))
            .field("high", float(row['high']))
            .field("low", float(row['low']))
            .field("close", float(row['close']))
            .field("volume", int(row['tick_volume']))
            .time(row['time'])
        )
        points.append(point)
    
    try:
        write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=points)
        print(f"   ✅ Wrote {len(points):,} points to InfluxDB")
    except Exception as e:
        print(f"   ❌ Write failed: {e}")
    finally:
        client.close()

def main():
    print("=" * 60)
    print("MT5 DATA ACQUISITION")
    print("=" * 60)
    
    # Connect to MT5
    if not connect_mt5():
        return
    
    # Collect data for each pair and timeframe
    total_candles = 0
    
    for symbol in PAIRS:
        for tf_name, tf_mt5 in TIMEFRAMES.items():
            df = get_historical_data(symbol, tf_name, tf_mt5)
            if df is not None:
                write_to_influxdb(df, symbol, tf_name)
                total_candles += len(df)
    
    # Disconnect
    mt5.shutdown()
    
    print("\n" + "=" * 60)
    print(f"✅ DATA ACQUISITION COMPLETE")
    print(f"   Total candles: {total_candles:,}")
    print("=" * 60)

if __name__ == "__main__":
    main()
