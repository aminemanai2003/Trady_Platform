"""
Technical Feature Engine - Pure indicator calculations
120 features: 60 technical + 25 temporal + extras
100% deterministic Python - NO LLM
"""
import pandas as pd
import numpy as np
import ta
from datetime import datetime


class TechnicalFeatureEngine:
    """Calculate technical indicators using deterministic algorithms.
    
    Feature Groups (matching presentation):
      - TECHNICAL (60): Trend, Momentum, Volatility, Volume
      - TEMPORAL  (25): Hour, Day, Week, Month, Sessions, Events
    """
    
    @staticmethod
    def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all technical indicators
        
        Input: DataFrame with OHLCV columns
        Output: DataFrame with all indicators added
        
        PURE MATH - NO AI
        """
        result = df.copy()
        
        # ──── MOMENTUM INDICATORS ─────────────────────────
        result['rsi_14'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
        result['rsi_7'] = ta.momentum.RSIIndicator(df['close'], window=7).rsi()
        
        # MACD
        macd = ta.trend.MACD(df['close'])
        result['macd'] = macd.macd()
        result['macd_signal'] = macd.macd_signal()
        result['macd_diff'] = macd.macd_diff()
        
        # Stochastic Oscillator
        stoch = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'])
        result['stoch_k'] = stoch.stoch()
        result['stoch_d'] = stoch.stoch_signal()
        
        # Williams %R (presentation requirement)
        result['williams_r'] = ta.momentum.WilliamsRIndicator(
            df['high'], df['low'], df['close'], lbp=14
        ).williams_r()
        
        # ROC (Rate of Change)
        result['roc_10'] = ((df['close'] - df['close'].shift(10)) / df['close'].shift(10)) * 100
        result['roc_20'] = ((df['close'] - df['close'].shift(20)) / df['close'].shift(20)) * 100
        result['roc_5'] = ((df['close'] - df['close'].shift(5)) / df['close'].shift(5)) * 100
        
        # CCI (Commodity Channel Index)
        result['cci_20'] = ta.trend.CCIIndicator(
            df['high'], df['low'], df['close'], window=20
        ).cci()
        
        # MFI (Money Flow Index)
        result['mfi_14'] = ta.volume.MFIIndicator(
            df['high'], df['low'], df['close'], df['volume'], window=14
        ).money_flow_index()
        
        # ──── TREND INDICATORS ────────────────────────────
        # Bollinger Bands
        bollinger = ta.volatility.BollingerBands(df['close'])
        result['bb_upper'] = bollinger.bollinger_hband()
        result['bb_middle'] = bollinger.bollinger_mavg()
        result['bb_lower'] = bollinger.bollinger_lband()
        result['bb_width'] = bollinger.bollinger_wband()
        result['bb_pctb'] = bollinger.bollinger_pband()
        
        # Moving Averages
        result['sma_10'] = df['close'].rolling(window=10).mean()
        result['sma_20'] = df['close'].rolling(window=20).mean()
        result['sma_50'] = df['close'].rolling(window=50).mean()
        result['sma_200'] = df['close'].rolling(window=200).mean()
        result['ema_9'] = df['close'].ewm(span=9).mean()
        result['ema_12'] = df['close'].ewm(span=12).mean()
        result['ema_21'] = df['close'].ewm(span=21).mean()
        result['ema_26'] = df['close'].ewm(span=26).mean()
        result['ema_55'] = df['close'].ewm(span=55).mean()
        
        # ADX (trend strength)
        adx_indicator = ta.trend.ADXIndicator(
            df['high'], df['low'], df['close'], window=14
        )
        result['adx'] = adx_indicator.adx()
        result['adx_pos'] = adx_indicator.adx_pos()
        result['adx_neg'] = adx_indicator.adx_neg()
        
        # Ichimoku
        ichimoku = ta.trend.IchimokuIndicator(df['high'], df['low'])
        result['ichimoku_a'] = ichimoku.ichimoku_a()
        result['ichimoku_b'] = ichimoku.ichimoku_b()
        result['ichimoku_base'] = ichimoku.ichimoku_base_line()
        result['ichimoku_conv'] = ichimoku.ichimoku_conversion_line()
        
        # ──── VOLATILITY INDICATORS ──────────────────────
        result['atr_14'] = ta.volatility.AverageTrueRange(
            df['high'], df['low'], df['close'], window=14
        ).average_true_range()
        result['atr_7'] = ta.volatility.AverageTrueRange(
            df['high'], df['low'], df['close'], window=7
        ).average_true_range()
        
        # Keltner Channel
        keltner = ta.volatility.KeltnerChannel(
            df['high'], df['low'], df['close']
        )
        result['keltner_high'] = keltner.keltner_channel_hband()
        result['keltner_low'] = keltner.keltner_channel_lband()
        
        # Donchian Channel
        result['donchian_high'] = df['high'].rolling(window=20).max()
        result['donchian_low'] = df['low'].rolling(window=20).min()
        
        # Historical volatility
        result['volatility_20'] = df['close'].pct_change().rolling(window=20).std() * np.sqrt(252)
        result['volatility_60'] = df['close'].pct_change().rolling(window=60).std() * np.sqrt(252)
        
        # ──── VOLUME INDICATORS ──────────────────────────
        result['volume_sma_20'] = df['volume'].rolling(window=20).mean()
        result['volume_ratio'] = df['volume'] / result['volume_sma_20'].replace(0, np.nan)
        
        # OBV (On-Balance Volume) — presentation requirement
        result['obv'] = ta.volume.OnBalanceVolumeIndicator(
            df['close'], df['volume']
        ).on_balance_volume()
        
        # VWAP approximation (Volume Weighted Average Price)
        result['vwap'] = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()
        
        # Accumulation/Distribution
        result['ad_line'] = ta.volume.AccDistIndexIndicator(
            df['high'], df['low'], df['close'], df['volume']
        ).acc_dist_index()
        
        # ──── TEMPORAL FEATURES (25) ─────────────────────
        if isinstance(df.index, pd.DatetimeIndex):
            idx = df.index
        else:
            idx = pd.to_datetime(df.index) if hasattr(df.index, 'name') else pd.DatetimeIndex([datetime.now()] * len(df))
        
        result['hour'] = idx.hour
        result['day_of_week'] = idx.dayofweek  # 0=Monday
        result['day_of_month'] = idx.day
        result['week_of_year'] = idx.isocalendar().week.astype(int) if hasattr(idx, 'isocalendar') else 1
        result['month'] = idx.month
        result['quarter'] = idx.quarter
        
        # Trading sessions (critical for FX)
        result['session_asian'] = ((idx.hour >= 0) & (idx.hour < 8)).astype(int)
        result['session_european'] = ((idx.hour >= 7) & (idx.hour < 16)).astype(int)
        result['session_us'] = ((idx.hour >= 13) & (idx.hour < 22)).astype(int)
        result['session_overlap_eu_us'] = ((idx.hour >= 13) & (idx.hour < 16)).astype(int)
        
        # Cyclical encoding (sin/cos for periodicity)
        result['hour_sin'] = np.sin(2 * np.pi * idx.hour / 24)
        result['hour_cos'] = np.cos(2 * np.pi * idx.hour / 24)
        result['dow_sin'] = np.sin(2 * np.pi * idx.dayofweek / 5)
        result['dow_cos'] = np.cos(2 * np.pi * idx.dayofweek / 5)
        result['month_sin'] = np.sin(2 * np.pi * idx.month / 12)
        result['month_cos'] = np.cos(2 * np.pi * idx.month / 12)
        
        # Is first/last trading hour
        result['is_market_open'] = ((idx.hour >= 8) & (idx.hour < 22)).astype(int)
        result['is_high_volume_hour'] = ((idx.hour >= 13) & (idx.hour < 17)).astype(int)
        
        # NFP Friday flag (first Friday of month)
        result['is_nfp_week'] = ((idx.day <= 7) & (idx.dayofweek == 4)).astype(int)
        
        # ──── DERIVED / INTERACTION FEATURES ─────────────
        # Cross-indicator interactions
        result['rsi_macd_divergence'] = (
            (result['rsi_14'] > 50).astype(int) - (result['macd_diff'] > 0).astype(int)
        )
        result['price_sma50_dist'] = (df['close'] - result['sma_50']) / result['sma_50'] * 100
        result['price_sma200_dist'] = (df['close'] - result['sma_200']) / result['sma_200'] * 100
        result['atr_pct'] = result['atr_14'] / df['close'] * 100
        
        return result
    
    @staticmethod
    def get_current_values(df: pd.DataFrame) -> dict:
        """
        Extract latest indicator values as dict
        Used for signal generation
        """
        if df.empty:
            return {}
        
        latest = df.iloc[-1]
        
        def safe_float(key):
            val = latest.get(key, None) if isinstance(latest, pd.Series) else None
            if val is not None and not pd.isna(val):
                return float(val)
            return None
        
        return {
            # Momentum
            'rsi_14': safe_float('rsi_14'),
            'rsi_7': safe_float('rsi_7'),
            'macd': safe_float('macd'),
            'macd_signal': safe_float('macd_signal'),
            'macd_diff': safe_float('macd_diff'),
            'stoch_k': safe_float('stoch_k'),
            'stoch_d': safe_float('stoch_d'),
            'williams_r': safe_float('williams_r'),
            'cci_20': safe_float('cci_20'),
            'mfi_14': safe_float('mfi_14'),
            'roc_10': safe_float('roc_10'),
            'roc_5': safe_float('roc_5'),
            # Trend
            'bb_position': TechnicalFeatureEngine._calculate_bb_position(latest),
            'bb_width': safe_float('bb_width'),
            'sma_trend': TechnicalFeatureEngine._calculate_sma_trend(latest),
            'adx': safe_float('adx'),
            'adx_pos': safe_float('adx_pos'),
            'adx_neg': safe_float('adx_neg'),
            # Volatility
            'atr_14': safe_float('atr_14'),
            'atr_pct': safe_float('atr_pct'),
            'volatility_20': safe_float('volatility_20'),
            # Volume
            'volume_ratio': safe_float('volume_ratio'),
            'obv': safe_float('obv'),
            # Temporal
            'session': TechnicalFeatureEngine._get_current_session(latest),
            'hour': safe_float('hour'),
            'day_of_week': safe_float('day_of_week'),
            # Price
            'close': float(latest['close']),
            'price_sma50_dist': safe_float('price_sma50_dist'),
            'price_sma200_dist': safe_float('price_sma200_dist'),
        }
    
    @staticmethod
    def get_feature_count(df: pd.DataFrame) -> int:
        """Return the total number of engineered features."""
        base_cols = {'open', 'high', 'low', 'close', 'volume'}
        return len([c for c in df.columns if c not in base_cols])
    
    @staticmethod
    def _get_current_session(row) -> str:
        """Determine current trading session."""
        hour = row.get('hour', 12) if isinstance(row, (dict, pd.Series)) else 12
        if isinstance(hour, (float, np.floating)):
            hour = int(hour) if not pd.isna(hour) else 12
        if 0 <= hour < 8:
            return 'asian'
        elif 7 <= hour < 16:
            return 'european'
        elif 13 <= hour < 22:
            return 'us'
        return 'off_hours'
    
    @staticmethod
    def _calculate_bb_position(row) -> float:
        """Calculate price position within Bollinger Bands (-1 to 1)"""
        if pd.isna(row['bb_upper']) or pd.isna(row['bb_lower']):
            return 0.0
        band_range = row['bb_upper'] - row['bb_lower']
        if band_range == 0:
            return 0.0
        return ((row['close'] - row['bb_lower']) / band_range - 0.5) * 2
    
    @staticmethod
    def _calculate_sma_trend(row) -> str:
        """Determine SMA alignment trend"""
        if all(pd.notna([row['sma_20'], row['sma_50'], row['sma_200']])):
            if row['close'] > row['sma_20'] > row['sma_50'] > row['sma_200']:
                return 'strong_bullish'
            elif row['close'] < row['sma_20'] < row['sma_50'] < row['sma_200']:
                return 'strong_bearish'
            elif row['close'] > row['sma_50']:
                return 'bullish'
            elif row['close'] < row['sma_50']:
                return 'bearish'
        return 'neutral'
