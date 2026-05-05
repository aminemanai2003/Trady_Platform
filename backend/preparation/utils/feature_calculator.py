"""
Feature Calculator Module
Calculate technical indicators and engineered features for forex trading
"""

import pandas as pd
import numpy as np
from loguru import logger
from typing import Dict, List, Optional
import sys

# Configure logger
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")


class FeatureCalculator:
    """Calculate technical indicators and features"""
    
    def __init__(self):
        """Initialize FeatureCalculator"""
        self.features_created = []
    
    # ============================================
    # PRICE-BASED FEATURES
    # ============================================
    
    def add_returns(self, df: pd.DataFrame, periods: List[int] = [1, 5, 10, 20]) -> pd.DataFrame:
        """
        Calculate returns over various periods
        
        Args:
            df: DataFrame with 'close' column
            periods: List of periods to calculate returns
            
        Returns:
            DataFrame with return columns added
        """
        logger.info(f"Calculating returns for periods: {periods}")
        
        df_feat = df.copy()
        
        for period in periods:
            col_name = f'return_{period}d'
            df_feat[col_name] = df_feat['close'].pct_change(periods=period)
            self.features_created.append(col_name)
        
        # Log returns (more stable for ML)
        for period in periods:
            col_name = f'log_return_{period}d'
            df_feat[col_name] = np.log(df_feat['close'] / df_feat['close'].shift(period))
            self.features_created.append(col_name)
        
        logger.info(f"✓ Added {len(periods)*2} return features")
        return df_feat
    
    def add_volatility(self, df: pd.DataFrame, windows: List[int] = [5, 10, 20, 50]) -> pd.DataFrame:
        """
        Calculate volatility (rolling standard deviation of returns)
        
        Args:
            df: DataFrame with 'close' column
            windows: List of window sizes
            
        Returns:
            DataFrame with volatility columns added
        """
        logger.info(f"Calculating volatility for windows: {windows}")
        
        df_feat = df.copy()
        
        # Calculate daily returns if not present
        if 'return_1d' not in df_feat.columns:
            df_feat['return_1d'] = df_feat['close'].pct_change()
        
        for window in windows:
            col_name = f'volatility_{window}d'
            df_feat[col_name] = df_feat['return_1d'].rolling(window=window).std()
            self.features_created.append(col_name)
        
        logger.info(f"✓ Added {len(windows)} volatility features")
        return df_feat
    
    # ============================================
    # MOVING AVERAGES
    # ============================================
    
    def add_moving_averages(self, df: pd.DataFrame, periods: List[int] = [7, 14, 21, 50, 100, 200]) -> pd.DataFrame:
        """
        Calculate Simple Moving Averages (SMA) and Exponential Moving Averages (EMA)
        
        Args:
            df: DataFrame with 'close' column
            periods: List of MA periods
            
        Returns:
            DataFrame with MA columns added
        """
        logger.info(f"Calculating moving averages for periods: {periods}")
        
        df_feat = df.copy()
        
        for period in periods:
            # Simple Moving Average
            sma_col = f'sma_{period}'
            df_feat[sma_col] = df_feat['close'].rolling(window=period).mean()
            self.features_created.append(sma_col)
            
            # Exponential Moving Average
            ema_col = f'ema_{period}'
            df_feat[ema_col] = df_feat['close'].ewm(span=period, adjust=False).mean()
            self.features_created.append(ema_col)
            
            # Price relative to MA (crossover signals)
            df_feat[f'price_to_sma_{period}'] = df_feat['close'] / df_feat[sma_col] - 1
            self.features_created.append(f'price_to_sma_{period}')
        
        logger.info(f"✓ Added {len(periods)*3} moving average features")
        return df_feat
    
    # ============================================
    # MOMENTUM INDICATORS
    # ============================================
    
    def add_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        Calculate Relative Strength Index (RSI)
        
        Args:
            df: DataFrame with 'close' column
            period: RSI period (default 14)
            
        Returns:
            DataFrame with RSI column added
        """
        logger.info(f"Calculating RSI (period={period})")
        
        df_feat = df.copy()
        
        # Calculate price changes
        delta = df_feat['close'].diff()
        
        # Separate gains and losses
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        
        # Calculate average gains and losses
        avg_gains = gains.rolling(window=period).mean()
        avg_losses = losses.rolling(window=period).mean()
        
        # Calculate RS and RSI
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        df_feat[f'rsi_{period}'] = rsi
        self.features_created.append(f'rsi_{period}')
        
        # RSI zones (overbought/oversold)
        df_feat[f'rsi_{period}_overbought'] = (rsi > 70).astype(int)
        df_feat[f'rsi_{period}_oversold'] = (rsi < 30).astype(int)
        self.features_created.extend([f'rsi_{period}_overbought', f'rsi_{period}_oversold'])
        
        logger.info(f"✓ Added RSI features")
        return df_feat
    
    def add_macd(self, df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """
        Calculate MACD (Moving Average Convergence Divergence)
        
        Args:
            df: DataFrame with 'close' column
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line period
            
        Returns:
            DataFrame with MACD columns added
        """
        logger.info(f"Calculating MACD ({fast}/{slow}/{signal})")
        
        df_feat = df.copy()
        
        # Calculate EMAs
        ema_fast = df_feat['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df_feat['close'].ewm(span=slow, adjust=False).mean()
        
        # MACD line
        macd = ema_fast - ema_slow
        df_feat['macd'] = macd
        self.features_created.append('macd')
        
        # Signal line
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        df_feat['macd_signal'] = signal_line
        self.features_created.append('macd_signal')
        
        # MACD histogram
        df_feat['macd_histogram'] = macd - signal_line
        self.features_created.append('macd_histogram')
        
        # MACD crossover signals
        df_feat['macd_bullish'] = ((macd > signal_line) & (macd.shift(1) <= signal_line.shift(1))).astype(int)
        df_feat['macd_bearish'] = ((macd < signal_line) & (macd.shift(1) >= signal_line.shift(1))).astype(int)
        self.features_created.extend(['macd_bullish', 'macd_bearish'])
        
        logger.info(f"✓ Added MACD features")
        return df_feat
    
    def add_stochastic(self, df: pd.DataFrame, period: int = 14, smooth_k: int = 3, smooth_d: int = 3) -> pd.DataFrame:
        """
        Calculate Stochastic Oscillator
        
        Args:
            df: DataFrame with 'high', 'low', 'close' columns
            period: Look-back period
            smooth_k: %K smoothing
            smooth_d: %D smoothing
            
        Returns:
            DataFrame with Stochastic columns added
        """
        logger.info(f"Calculating Stochastic Oscillator (period={period})")
        
        df_feat = df.copy()
        
        # Calculate %K
        low_min = df_feat['low'].rolling(window=period).min()
        high_max = df_feat['high'].rolling(window=period).max()
        
        stoch_k = 100 * (df_feat['close'] - low_min) / (high_max - low_min)
        stoch_k_smooth = stoch_k.rolling(window=smooth_k).mean()
        
        df_feat[f'stoch_k_{period}'] = stoch_k_smooth
        self.features_created.append(f'stoch_k_{period}')
        
        # Calculate %D (signal line)
        stoch_d = stoch_k_smooth.rolling(window=smooth_d).mean()
        df_feat[f'stoch_d_{period}'] = stoch_d
        self.features_created.append(f'stoch_d_{period}')
        
        logger.info(f"✓ Added Stochastic features")
        return df_feat
    
    # ============================================
    # VOLATILITY INDICATORS
    # ============================================
    
    def add_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std: float = 2.0) -> pd.DataFrame:
        """
        Calculate Bollinger Bands
        
        Args:
            df: DataFrame with 'close' column
            period: MA period
            std: Number of standard deviations
            
        Returns:
            DataFrame with Bollinger Band columns added
        """
        logger.info(f"Calculating Bollinger Bands (period={period}, std={std})")
        
        df_feat = df.copy()
        
        # Middle band (SMA)
        sma = df_feat['close'].rolling(window=period).mean()
        df_feat[f'bb_middle_{period}'] = sma
        self.features_created.append(f'bb_middle_{period}')
        
        # Standard deviation
        rolling_std = df_feat['close'].rolling(window=period).std()
        
        # Upper and lower bands
        df_feat[f'bb_upper_{period}'] = sma + (std * rolling_std)
        df_feat[f'bb_lower_{period}'] = sma - (std * rolling_std)
        self.features_created.extend([f'bb_upper_{period}', f'bb_lower_{period}'])
        
        # Bandwidth
        df_feat[f'bb_bandwidth_{period}'] = (df_feat[f'bb_upper_{period}'] - df_feat[f'bb_lower_{period}']) / sma
        self.features_created.append(f'bb_bandwidth_{period}')
        
        # %B (position within bands)
        df_feat[f'bb_percent_{period}'] = (df_feat['close'] - df_feat[f'bb_lower_{period}']) / (df_feat[f'bb_upper_{period}'] - df_feat[f'bb_lower_{period}'])
        self.features_created.append(f'bb_percent_{period}')
        
        logger.info(f"✓ Added Bollinger Band features")
        return df_feat
    
    def add_atr(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        Calculate Average True Range (ATR)
        
        Args:
            df: DataFrame with 'high', 'low', 'close' columns
            period: ATR period
            
        Returns:
            DataFrame with ATR column added
        """
        logger.info(f"Calculating ATR (period={period})")
        
        df_feat = df.copy()
        
        # True Range
        high_low = df_feat['high'] - df_feat['low']
        high_close = np.abs(df_feat['high'] - df_feat['close'].shift())
        low_close = np.abs(df_feat['low'] - df_feat['close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        
        # Average True Range
        atr = true_range.rolling(window=period).mean()
        df_feat[f'atr_{period}'] = atr
        self.features_created.append(f'atr_{period}')
        
        # Normalized ATR (as % of price)
        df_feat[f'atr_{period}_pct'] = (atr / df_feat['close']) * 100
        self.features_created.append(f'atr_{period}_pct')
        
        logger.info(f"✓ Added ATR features")
        return df_feat
    
    # ============================================
    # VOLUME INDICATORS (if volume available)
    # ============================================
    
    def add_volume_features(self, df: pd.DataFrame, periods: List[int] = [5, 10, 20]) -> pd.DataFrame:
        """
        Calculate volume-based features
        
        Args:
            df: DataFrame with 'volume' column
            periods: Periods for volume averages
            
        Returns:
            DataFrame with volume features added
        """
        if 'volume' not in df.columns or df['volume'].sum() == 0:
            logger.warning("Volume data not available, skipping volume features")
            return df
        
        logger.info(f"Calculating volume features for periods: {periods}")
        
        df_feat = df.copy()
        
        for period in periods:
            # Volume moving average
            df_feat[f'volume_ma_{period}'] = df_feat['volume'].rolling(window=period).mean()
            self.features_created.append(f'volume_ma_{period}')
            
            # Volume ratio (current vs average)
            df_feat[f'volume_ratio_{period}'] = df_feat['volume'] / df_feat[f'volume_ma_{period}']
            self.features_created.append(f'volume_ratio_{period}')
        
        logger.info(f"✓ Added volume features")
        return df_feat
    
    # ============================================
    # PATTERN & SIGNAL FEATURES
    # ============================================
    
    def add_price_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Identify price patterns and signals
        
        Args:
            df: DataFrame with OHLC columns
            
        Returns:
            DataFrame with pattern features added
        """
        logger.info("Identifying price patterns")
        
        df_feat = df.copy()
        
        # Doji candle (open ≈ close)
        body = np.abs(df_feat['close'] - df_feat['open'])
        range_hl = df_feat['high'] - df_feat['low']
        df_feat['doji'] = (body / range_hl < 0.1).astype(int)
        self.features_created.append('doji')
        
        # Bullish/Bearish candles
        df_feat['bullish_candle'] = (df_feat['close'] > df_feat['open']).astype(int)
        df_feat['bearish_candle'] = (df_feat['close'] < df_feat['open']).astype(int)
        self.features_created.extend(['bullish_candle', 'bearish_candle'])
        
        # Upper/Lower shadows
        df_feat['upper_shadow'] = df_feat['high'] - df_feat[['open', 'close']].max(axis=1)
        df_feat['lower_shadow'] = df_feat[['open', 'close']].min(axis=1) - df_feat['low']
        self.features_created.extend(['upper_shadow', 'lower_shadow'])
        
        # Gap up/down
        df_feat['gap_up'] = (df_feat['open'] > df_feat['high'].shift()).astype(int)
        df_feat['gap_down'] = (df_feat['open'] < df_feat['low'].shift()).astype(int)
        self.features_created.extend(['gap_up', 'gap_down'])
        
        logger.info(f"✓ Added pattern features")
        return df_feat
    
    # ============================================
    # TIME-BASED FEATURES
    # ============================================
    
    def add_time_features(self, df: pd.DataFrame, time_column: str = 'time') -> pd.DataFrame:
        """
        Extract time-based features
        
        Args:
            df: DataFrame with datetime column
            time_column: Name of datetime column
            
        Returns:
            DataFrame with time features added
        """
        logger.info("Extracting time features")
        
        df_feat = df.copy()
        
        # Ensure datetime type
        df_feat[time_column] = pd.to_datetime(df_feat[time_column])
        
        # Extract components
        df_feat['year'] = df_feat[time_column].dt.year
        df_feat['month'] = df_feat[time_column].dt.month
        df_feat['day'] = df_feat[time_column].dt.day
        df_feat['dayofweek'] = df_feat[time_column].dt.dayofweek
        df_feat['hour'] = df_feat[time_column].dt.hour
        df_feat['quarter'] = df_feat[time_column].dt.quarter
        
        self.features_created.extend(['year', 'month', 'day', 'dayofweek', 'hour', 'quarter'])
        
        # Cyclical encoding (for hour and day)
        df_feat['hour_sin'] = np.sin(2 * np.pi * df_feat['hour'] / 24)
        df_feat['hour_cos'] = np.cos(2 * np.pi * df_feat['hour'] / 24)
        df_feat['day_sin'] = np.sin(2 * np.pi * df_feat['dayofweek'] / 7)
        df_feat['day_cos'] = np.cos(2 * np.pi * df_feat['dayofweek'] / 7)
        
        self.features_created.extend(['hour_sin', 'hour_cos', 'day_sin', 'day_cos'])
        
        # Trading session indicators
        df_feat['asian_session'] = ((df_feat['hour'] >= 0) & (df_feat['hour'] < 8)).astype(int)
        df_feat['european_session'] = ((df_feat['hour'] >= 8) & (df_feat['hour'] < 16)).astype(int)
        df_feat['american_session'] = ((df_feat['hour'] >= 16) & (df_feat['hour'] < 24)).astype(int)
        
        self.features_created.extend(['asian_session', 'european_session', 'american_session'])
        
        logger.info(f"✓ Added time features")
        return df_feat
    
    # ============================================
    # ALL-IN-ONE METHOD
    # ============================================
    
    def calculate_all_features(self, df: pd.DataFrame, config: Optional[Dict] = None) -> pd.DataFrame:
        """
        Calculate all technical features
        
        Args:
            df: DataFrame with OHLC data
            config: Optional configuration dictionary
            
        Returns:
            DataFrame with all features added
        """
        logger.info("=" * 60)
        logger.info("CALCULATING ALL TECHNICAL FEATURES")
        logger.info("=" * 60)
        
        df_feat = df.copy()
        self.features_created = []
        
        # Use default config if not provided
        if config is None:
            config = {
                'return_periods': [1, 5, 10, 20],
                'volatility_windows': [5, 10, 20],
                'ma_periods': [7, 14, 21, 50, 100, 200],
                'rsi_period': 14,
                'macd': {'fast': 12, 'slow': 26, 'signal': 9},
                'stoch_period': 14,
                'bb_period': 20,
                'atr_period': 14
            }
        
        # Calculate features
        df_feat = self.add_returns(df_feat, periods=config.get('return_periods', [1, 5, 10, 20]))
        df_feat = self.add_volatility(df_feat, windows=config.get('volatility_windows', [5, 10, 20]))
        df_feat = self.add_moving_averages(df_feat, periods=config.get('ma_periods', [7, 14, 21, 50]))
        df_feat = self.add_rsi(df_feat, period=config.get('rsi_period', 14))
        
        macd_config = config.get('macd', {})
        df_feat = self.add_macd(df_feat, 
                               fast=macd_config.get('fast', 12),
                               slow=macd_config.get('slow', 26),
                               signal=macd_config.get('signal', 9))
        
        df_feat = self.add_stochastic(df_feat, period=config.get('stoch_period', 14))
        df_feat = self.add_bollinger_bands(df_feat, period=config.get('bb_period', 20))
        
        if 'high' in df_feat.columns and 'low' in df_feat.columns:
            df_feat = self.add_atr(df_feat, period=config.get('atr_period', 14))
            df_feat = self.add_price_patterns(df_feat)
        
        if 'volume' in df_feat.columns:
            df_feat = self.add_volume_features(df_feat)
        
        if 'time' in df_feat.columns or df_feat.index.name == 'time':
            df_feat = self.add_time_features(df_feat)
        
        logger.info("=" * 60)
        logger.info(f"✓ TOTAL FEATURES CREATED: {len(self.features_created)}")
        logger.info(f"✓ DataFrame shape: {df.shape} → {df_feat.shape}")
        logger.info("=" * 60)
        
        return df_feat
    
    def get_feature_list(self) -> List[str]:
        """Get list of created features"""
        return self.features_created.copy()


if __name__ == '__main__':
    # Test the FeatureCalculator
    
    # Create sample OHLC data
    dates = pd.date_range('2020-01-01', periods=200, freq='D')
    np.random.seed(42)
    
    close_prices = 100 + np.cumsum(np.random.randn(200) * 0.5)
    
    data = {
        'time': dates,
        'open': close_prices + np.random.randn(200) * 0.2,
        'high': close_prices + np.abs(np.random.randn(200)) * 0.5,
        'low': close_prices - np.abs(np.random.randn(200)) * 0.5,
        'close': close_prices,
        'volume': np.random.randint(1000, 10000, 200)
    }
    
    df_test = pd.DataFrame(data)
    
    print("\n" + "=" * 60)
    print("TESTING FEATURE CALCULATOR")
    print("=" * 60)
    print(f"Original shape: {df_test.shape}")
    
    calculator = FeatureCalculator()
    df_features = calculator.calculate_all_features(df_test)
    
    print(f"With features shape: {df_features.shape}")
    print(f"\nTotal features created: {len(calculator.get_feature_list())}")
    print("\nSample features:")
    for feat in calculator.get_feature_list()[:10]:
        print(f"  - {feat}")
    print("  ...")
    print("=" * 60)
