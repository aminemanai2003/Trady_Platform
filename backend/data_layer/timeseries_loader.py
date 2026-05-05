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

    @staticmethod
    def _timeframe_values(timeframe: str) -> List[str]:
        tf = (timeframe or "1h").strip()
        values = [tf]
        tf_upper = tf.upper()
        tf_lower = tf.lower()
        if tf_upper not in values:
            values.append(tf_upper)
        if tf_lower not in values:
            values.append(tf_lower)
        return values

    def latest_timestamp(
        self,
        timeframe: str = "1h",
        symbols: Optional[List[str]] = None,
        lookback_days: int = 365,
    ) -> Optional[datetime]:
        """Return the latest OHLCV timestamp available in InfluxDB."""
        timeframe_values = self._timeframe_values(timeframe)
        timeframe_conditions = " or ".join([f'r["timeframe"] == "{tf}"' for tf in timeframe_values])

        symbol_filter = ""
        if symbols:
            symbol_conditions = " or ".join([f'r["symbol"] == "{symbol}"' for symbol in symbols])
            symbol_filter = f"|> filter(fn: (r) => {symbol_conditions})"

        query = f"""
        from(bucket: "{settings.INFLUX_BUCKET}")
            |> range(start: -{int(lookback_days)}d)
            |> filter(fn: (r) => {timeframe_conditions})
            |> filter(fn: (r) => r["_field"] == "close")
            {symbol_filter}
            |> sort(columns: ["_time"], desc: true)
            |> limit(n: 1)
        """

        try:
            with DatabaseManager.get_influx_client() as client:
                df = client.query_api().query_data_frame(query)

            if df is None:
                return None

            if isinstance(df, list):
                if not df:
                    return None
                df = pd.concat(df, ignore_index=True)

            if df.empty or "_time" not in df.columns:
                influx_ts = None
            else:
                influx_ts = pd.to_datetime(df.iloc[0]["_time"]).to_pydatetime().replace(tzinfo=None)
        except Exception:
            influx_ts = None

        # Compare with SQLite and return the most recent timestamp
        sqlite_ts = self._sqlite_latest_timestamp(timeframe, symbols)
        if influx_ts is None and sqlite_ts is None:
            return None
        if influx_ts is None:
            return sqlite_ts
        if sqlite_ts is None:
            return influx_ts
        return max(influx_ts, sqlite_ts)

    def _sqlite_latest_timestamp(
        self,
        timeframe: str = "1h",
        symbols: Optional[List[str]] = None,
    ) -> Optional[datetime]:
        """Read latest OHLCV timestamp from SQLite OHLCVCandle model."""
        try:
            from scheduling.models import OHLCVCandle
            qs = OHLCVCandle.objects.filter(timeframe=timeframe)
            if symbols:
                qs = qs.filter(symbol__in=symbols)
            latest = qs.order_by('-timestamp').values_list('timestamp', flat=True).first()
            if latest is None:
                return None
            return latest.replace(tzinfo=None) if latest.tzinfo else latest
        except Exception:
            return None
    
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
        timeframe_values = self._timeframe_values(timeframe)
        timeframe_conditions = " or ".join([f'r["timeframe"] == "{tf}"' for tf in timeframe_values])
        
        query = f"""
        from(bucket: "{settings.INFLUX_BUCKET}")
            |> range(start: {start_rfc}, stop: {end_rfc})
            |> filter(fn: (r) => r["symbol"] == "{symbol}")
            |> filter(fn: (r) => {timeframe_conditions})
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        """
        
        result = None
        try:
            with DatabaseManager.get_influx_client() as client:
                result = client.query_api().query_data_frame(query)
        except Exception as _influx_err:
            import logging as _log
            _log.getLogger(__name__).warning(f"InfluxDB unavailable ({_influx_err}), falling back to SQLite")

        # ── SQLite fallback (always attempted when InfluxDB fails or returns empty) ──
        if result is None or (isinstance(result, pd.DataFrame) and result.empty) or (isinstance(result, list) and not result):
            try:
                from scheduling.models import OHLCVCandle
                qs = OHLCVCandle.objects.filter(symbol=symbol).order_by('timestamp')
                if start_time:
                    qs = qs.filter(timestamp__gte=start_time)
                if end_time:
                    qs = qs.filter(timestamp__lte=end_time)
                rows = list(qs.values('timestamp', 'open', 'high', 'low', 'close', 'volume'))
                if rows:
                    return pd.DataFrame(rows)
            except Exception as _sqlite_err:
                import logging as _log2
                _log2.getLogger(__name__).warning(f"SQLite OHLCV fallback failed: {_sqlite_err}")
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

        if isinstance(result, list):
            frames = [f for f in result if isinstance(f, pd.DataFrame) and not f.empty]
            if not frames:
                return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            result = pd.concat(frames, ignore_index=True)

        if isinstance(result, pd.DataFrame) and result.empty:
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

        required_cols = {'_time', 'open', 'high', 'low', 'close', 'volume'}
        if not required_cols.issubset(set(result.columns)):
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
