"""
PHASE 2: Technical Features Calculator
RSI, MACD, Bollinger Bands, ATR, Volatility, Trend, Support/Resistance
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
import ta  # Technical Analysis library

from core.database import TimeSeriesQuery
from features.models import TechnicalFeatures


class TechnicalFeaturesCalculator:
    """Calculate technical indicators for trading signals"""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
    
    def calculate_all(self, start_time: str, end_time: str) -> pd.DataFrame:
        """Calculate all technical features"""
        
        # Fetch OHLCV data
        df = self._fetch_ohlcv(start_time, end_time)
        
        if len(df) < 100:  # Need minimum data for indicators
            raise ValueError(f"Insufficient data: {len(df)} candles")
        
        # Calculate indicators
        df = self._calculate_rsi(df)
        df = self._calculate_macd(df)
        df = self._calculate_bollinger_bands(df)
        df = self._calculate_atr(df)
        df = self._calculate_volatility(df)
        df = self._calculate_trend(df)
        df = self._calculate_support_resistance(df)
        
        # Save to database
        self._save_features(df)
        
        return df
    
    def _fetch_ohlcv(self, start_time: str, end_time: str) -> pd.DataFrame:
        """Fetch OHLCV data from InfluxDB"""
        result = TimeSeriesQuery.query_ohlcv(self.symbol, start_time, end_time)
        
        records = []
        for table in result:
            for record in table.records:
                records.append({
                    'time': record.get_time(),
                    'open': record.values.get('open'),
                    'high': record.values.get('high'),
                    'low': record.values.get('low'),
                    'close': record.values.get('close'),
                    'volume': record.values.get('volume', 0)
                })
        
        df = pd.DataFrame(records)
        df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values('time').reset_index(drop=True)
        
        return df
    
    def _calculate_rsi(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate RSI (Relative Strength Index)"""
        df['rsi_14'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()
        df['rsi_28'] = ta.momentum.RSIIndicator(close=df['close'], window=28).rsi()
        return df
    
    def _calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        macd_indicator = ta.trend.MACD(
            close=df['close'],
            window_slow=26,
            window_fast=12,
            window_sign=9
        )
        
        df['macd'] = macd_indicator.macd()
        df['macd_signal'] = macd_indicator.macd_signal()
        df['macd_diff'] = macd_indicator.macd_diff()
        
        return df
    
    def _calculate_bollinger_bands(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Bollinger Bands"""
        bb_indicator = ta.volatility.BollingerBands(
            close=df['close'],
            window=20,
            window_dev=2
        )
        
        df['bb_upper'] = bb_indicator.bollinger_hband()
        df['bb_middle'] = bb_indicator.bollinger_mavg()
        df['bb_lower'] = bb_indicator.bollinger_lband()
        
        # Calculate band width and position
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # Position: 0 = at lower band, 0.5 = at middle, 1 = at upper band
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        df['bb_position'] = df['bb_position'].clip(0, 1)
        
        return df
    
    def _calculate_atr(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate ATR (Average True Range)"""
        df['atr_14'] = ta.volatility.AverageTrueRange(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            window=14
        ).average_true_range()
        
        return df
    
    def _calculate_volatility(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate rolling volatility"""
        # Log returns
        log_returns = np.log(df['close'] / df['close'].shift(1))
        
        # Rolling standard deviation (annualized)
        df['rolling_vol_20'] = log_returns.rolling(window=20).std() * np.sqrt(252)
        df['rolling_vol_60'] = log_returns.rolling(window=60).std() * np.sqrt(252)
        
        return df
    
    def _calculate_trend(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate trend using linear regression slope"""
        
        def calculate_slope(series, window):
            """Calculate rolling regression slope"""
            slopes = []
            for i in range(len(series)):
                if i < window:
                    slopes.append(np.nan)
                else:
                    y = series.iloc[i-window:i].values
                    x = np.arange(window)
                    # Linear regression
                    slope = np.polyfit(x, y, 1)[0]
                    slopes.append(slope)
            return pd.Series(slopes, index=series.index)
        
        df['trend_slope_20'] = calculate_slope(df['close'], 20)
        df['trend_slope_60'] = calculate_slope(df['close'], 60)
        
        return df
    
    def _calculate_support_resistance(self, df: pd.DataFrame, 
                                      lookback: int = 50) -> pd.DataFrame:
        """
        Identify support and resistance levels
        Using local minima/maxima approach
        """
        
        def find_support_resistance(close_prices, window=5):
            """Find local support and resistance levels"""
            supports = []
            resistances = []
            
            for i in range(len(close_prices)):
                if i < window or i >= len(close_prices) - window:
                    supports.append(np.nan)
                    resistances.append(np.nan)
                    continue
                
                # Look for local minima (support)
                window_slice = close_prices.iloc[i-window:i+window+1]
                current_price = close_prices.iloc[i]
                
                # Find recent support (local minimum)
                recent_lows = close_prices.iloc[max(0, i-lookback):i].rolling(window=5).min()
                support = recent_lows.min() if len(recent_lows) > 0 else current_price
                
                # Find recent resistance (local maximum)
                recent_highs = close_prices.iloc[max(0, i-lookback):i].rolling(window=5).max()
                resistance = recent_highs.max() if len(recent_highs) > 0 else current_price
                
                supports.append(support)
                resistances.append(resistance)
            
            return pd.Series(supports), pd.Series(resistances)
        
        support, resistance = find_support_resistance(df['close'])
        
        # Calculate distance to support/resistance (as percentage)
        df['distance_to_support'] = (df['close'] - support) / df['close']
        df['distance_to_resistance'] = (resistance - df['close']) / df['close']
        
        return df
    
    def _save_features(self, df: pd.DataFrame):
        """Save calculated features to database"""
        
        # Bulk create for efficiency
        features_to_create = []
        
        for _, row in df.iterrows():
            if pd.notna(row['time']):
                features_to_create.append(
                    TechnicalFeatures(
                        symbol=self.symbol,
                        timestamp=row['time'],
                        rsi_14=row.get('rsi_14'),
                        rsi_28=row.get('rsi_28'),
                        macd=row.get('macd'),
                        macd_signal=row.get('macd_signal'),
                        macd_diff=row.get('macd_diff'),
                        bb_upper=row.get('bb_upper'),
                        bb_middle=row.get('bb_middle'),
                        bb_lower=row.get('bb_lower'),
                        bb_width=row.get('bb_width'),
                        bb_position=row.get('bb_position'),
                        atr_14=row.get('atr_14'),
                        rolling_vol_20=row.get('rolling_vol_20'),
                        rolling_vol_60=row.get('rolling_vol_60'),
                        trend_slope_20=row.get('trend_slope_20'),
                        trend_slope_60=row.get('trend_slope_60'),
                        distance_to_support=row.get('distance_to_support'),
                        distance_to_resistance=row.get('distance_to_resistance')
                    )
                )
        
        # Bulk insert
        TechnicalFeatures.objects.bulk_create(
            features_to_create,
            batch_size=1000,
            ignore_conflicts=True
        )
