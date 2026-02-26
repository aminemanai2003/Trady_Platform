"""
Technical Feature Engine - Pure indicator calculations
100% deterministic Python - NO LLM
"""
import pandas as pd
import numpy as np
import ta


class TechnicalFeatureEngine:
    """Calculate technical indicators using deterministic algorithms"""
    
    @staticmethod
    def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all technical indicators
        
        Input: DataFrame with OHLCV columns
        Output: DataFrame with all indicators added
        
        PURE MATH - NO AI
        """
        result = df.copy()
        
        # Momentum Indicators
        result['rsi_14'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
        result['rsi_7'] = ta.momentum.RSIIndicator(df['close'], window=7).rsi()
        
        # MACD
        macd = ta.trend.MACD(df['close'])
        result['macd'] = macd.macd()
        result['macd_signal'] = macd.macd_signal()
        result['macd_diff'] = macd.macd_diff()
        
        # Bollinger Bands
        bollinger = ta.volatility.BollingerBands(df['close'])
        result['bb_upper'] = bollinger.bollinger_hband()
        result['bb_middle'] = bollinger.bollinger_mavg()
        result['bb_lower'] = bollinger.bollinger_lband()
        result['bb_width'] = bollinger.bollinger_wband()
        
        # ATR (volatility)
        result['atr_14'] = ta.volatility.AverageTrueRange(
            df['high'], df['low'], df['close'], window=14
        ).average_true_range()
        
        # Moving Averages
        result['sma_20'] = df['close'].rolling(window=20).mean()
        result['sma_50'] = df['close'].rolling(window=50).mean()
        result['sma_200'] = df['close'].rolling(window=200).mean()
        result['ema_12'] = df['close'].ewm(span=12).mean()
        result['ema_26'] = df['close'].ewm(span=26).mean()
        
        # Stochastic
        stoch = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'])
        result['stoch_k'] = stoch.stoch()
        result['stoch_d'] = stoch.stoch_signal()
        
        # ADX (trend strength)
        result['adx'] = ta.trend.ADXIndicator(
            df['high'], df['low'], df['close'], window=14
        ).adx()
        
        # Volume indicators
        result['volume_sma_20'] = df['volume'].rolling(window=20).mean()
        result['volume_ratio'] = df['volume'] / result['volume_sma_20']
        
        # Price momentum
        result['roc_10'] = ((df['close'] - df['close'].shift(10)) / df['close'].shift(10)) * 100
        result['roc_20'] = ((df['close'] - df['close'].shift(20)) / df['close'].shift(20)) * 100
        
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
        return {
            'rsi_14': float(latest['rsi_14']) if not pd.isna(latest['rsi_14']) else None,
            'rsi_7': float(latest['rsi_7']) if not pd.isna(latest['rsi_7']) else None,
            'macd': float(latest['macd']) if not pd.isna(latest['macd']) else None,
            'macd_signal': float(latest['macd_signal']) if not pd.isna(latest['macd_signal']) else None,
            'macd_diff': float(latest['macd_diff']) if not pd.isna(latest['macd_diff']) else None,
            'bb_position': TechnicalFeatureEngine._calculate_bb_position(latest),
            'atr_14': float(latest['atr_14']) if not pd.isna(latest['atr_14']) else None,
            'sma_trend': TechnicalFeatureEngine._calculate_sma_trend(latest),
            'stoch_k': float(latest['stoch_k']) if not pd.isna(latest['stoch_k']) else None,
            'stoch_d': float(latest['stoch_d']) if not pd.isna(latest['stoch_d']) else None,
            'adx': float(latest['adx']) if not pd.isna(latest['adx']) else None,
            'volume_ratio': float(latest['volume_ratio']) if not pd.isna(latest['volume_ratio']) else None,
            'roc_10': float(latest['roc_10']) if not pd.isna(latest['roc_10']) else None,
            'close': float(latest['close'])
        }
    
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
