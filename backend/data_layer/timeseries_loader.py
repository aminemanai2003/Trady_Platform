"""
Time Series Data Loader - Pure data retrieval from InfluxDB
Supports multi-timeframe analysis (1H, 4H, D1, W1, M1)
No calculations, no logic - just clean data
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import pandas as pd
import numpy as np
from django.conf import settings
from core.database import DatabaseManager


class TimeSeriesLoader:
    """Load OHLCV data from InfluxDB with multi-timeframe support"""

    # Supported timeframes for multi-horizon analysis (DSO1.2)
    TIMEFRAMES = {
        '1h': {'label': 'Intraday', 'resample': None},
        '4h': {'label': 'Intraday Swing', 'resample': '4h'},
        '1d': {'label': 'Daily (Swing)', 'resample': '1D'},
        '1w': {'label': 'Weekly (Position)', 'resample': '1W'},
        '1M': {'label': 'Monthly (Position)', 'resample': '1ME'},
    }
    
    def __init__(self):
        pass
    
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
        
        # RFC3339 avec Z obligatoire pour Flux
        start_rfc = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_rfc = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        query = f"""
        from(bucket: "{settings.INFLUX_BUCKET}")
            |> range(start: {start_rfc}, stop: {end_rfc})
            |> filter(fn: (r) => r["symbol"] == "{symbol}")
            |> filter(fn: (r) => r["timeframe"] == "1h")
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        """
        
        try:
            with DatabaseManager.get_influx_client() as client:
                result = client.query_api().query_data_frame(query)
        except Exception:
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        if result is None or (isinstance(result, pd.DataFrame) and result.empty):
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Clean and standardize
        df = result[['_time', 'open', 'high', 'low', 'close', 'volume']].copy()
        df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        df = df.set_index('timestamp')

        # Resample to requested timeframe if needed
        if timeframe != '1h' and timeframe in self.TIMEFRAMES:
            resample_rule = self.TIMEFRAMES[timeframe]['resample']
            if resample_rule:
                df = self._resample_ohlcv(df, resample_rule)

        # Reset index for backward compatibility
        df = df.reset_index()
        
        return df

    def load_multi_timeframe(
        self,
        symbol: str,
        timeframes: List[str] = None,
        start_time: Optional[datetime] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        Load data across multiple timeframes for a single symbol.
        Key for multi-horizon analysis (DSO1.2: 1H, 4H, D1, W1, M1).
        
        Returns:
            Dict mapping timeframe -> DataFrame
        """
        if timeframes is None:
            timeframes = ['1h', '4h', '1d']

        results = {}
        for tf in timeframes:
            df = self.load_ohlcv(symbol, start_time=start_time, timeframe=tf)
            if not df.empty:
                results[tf] = df
        return results

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

    @staticmethod
    def _resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
        """
        Resample OHLCV data to a lower timeframe.
        Proper OHLCV aggregation: open=first, high=max, low=min, close=last, volume=sum.
        """
        resampled = df.resample(rule).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
        }).dropna()
        return resampled
