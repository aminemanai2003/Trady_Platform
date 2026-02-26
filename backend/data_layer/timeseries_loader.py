"""
Time Series Data Loader - Pure data retrieval from InfluxDB
No calculations, no logic - just clean data
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import pandas as pd
from core.database import DatabaseManager


class TimeSeriesLoader:
    """Load OHLCV data from InfluxDB"""
    
    def __init__(self):
        self.db = DatabaseManager()
    
    def load_ohlcv(
        self,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        timeframe: str = "1h"
    ) -> pd.DataFrame:
        """
        Load raw OHLCV data
        
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
            NO CALCULATIONS - just raw data
        """
        if start_time is None:
            start_time = datetime.now() - timedelta(days=90)
        if end_time is None:
            end_time = datetime.now()
        
        query = f"""
        from(bucket: "{self.db.influx_bucket}")
            |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
            |> filter(fn: (r) => r["symbol"] == "{symbol}")
            |> filter(fn: (r) => r["timeframe"] == "{timeframe}")
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        """
        
        with self.db.get_influx_client() as client:
            result = client.query_api().query_data_frame(query)
        
        if result.empty:
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Clean and standardize
        df = result[['_time', 'open', 'high', 'low', 'close', 'volume']].copy()
        df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        return df
    
    def load_multiple_symbols(
        self,
        symbols: List[str],
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        timeframe: str = "1h"
    ) -> Dict[str, pd.DataFrame]:
        """Load data for multiple symbols"""
        return {
            symbol: self.load_ohlcv(symbol, start_time, end_time, timeframe)
            for symbol in symbols
        }
