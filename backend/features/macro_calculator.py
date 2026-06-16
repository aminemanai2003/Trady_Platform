"""
PHASE 2: Macro Features Calculator
Rate differentials, inflation differential, surprise metrics, yield spread, risk sentiment
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple

from core.database import DatabaseManager
from features.models import MacroFeatures


class MacroFeaturesCalculator:
    """Calculate macro-economic features for FX pairs"""
    
    # Currency to country/region mapping
    CURRENCY_MAP = {
        'USD': 'US',
        'EUR': 'EU',
        'GBP': 'UK',
        'JPY': 'JP',
        'CHF': 'CH',
        'CAD': 'CA',
        'AUD': 'AU',
        'NZD': 'NZ'
    }
    
    def __init__(self, currency_pair: str):
        """
        currency_pair format: 'EURUSD' (base/quote)
        """
        self.currency_pair = currency_pair
        self.base_currency = currency_pair[:3]
        self.quote_currency = currency_pair[3:6]
        
        self.base_country = self.CURRENCY_MAP.get(self.base_currency)
        self.quote_country = self.CURRENCY_MAP.get(self.quote_currency)
    
    def calculate_all(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Calculate all macro features"""
        
        # Fetch macro data for both countries
        base_data = self._fetch_country_data(self.base_country, start_date, end_date)
        quote_data = self._fetch_country_data(self.quote_country, start_date, end_date)
        
        # Merge on date
        df = pd.merge(
            base_data, 
            quote_data, 
            on='date', 
            suffixes=('_base', '_quote'),
            how='outer'
        )
        df = df.sort_values('date').reset_index(drop=True)
        
        # Forward fill to handle different release schedules
        df = df.fillna(method='ffill', limit=30)
        
        # Calculate differentials
        df = self._calculate_rate_differential(df)
        df = self._calculate_inflation_differential(df)
        df = self._calculate_surprise_metric(df)
        df = self._calculate_yield_spread(df)
        df = self._calculate_risk_sentiment(df)
        df = self._calculate_gdp_growth_differential(df)
        
        # Save to database
        self._save_features(df)
        
        return df
    
    def _fetch_country_data(self, country: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch macro data for a specific country"""
        
        query = """
            SELECT 
                date,
                series_id,
                value,
                forecast_value
            FROM macro_data
            WHERE country_code = %s
            AND date >= %s AND date <= %s
            ORDER BY date, series_id
        """
        
        with DatabaseManager.get_postgres_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(country, start_date, end_date))
        
        # Pivot to wide format
        df_pivot = df.pivot(index='date', columns='series_id', values=['value', 'forecast_value'])
        df_pivot.columns = ['_'.join(col).strip() for col in df_pivot.columns.values]
        df_pivot = df_pivot.reset_index()
        
        return df_pivot
    
    def _calculate_rate_differential(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate interest rate differential (base - quote)"""
        
        # Try to find interest rate columns
        base_rate_cols = [col for col in df.columns if 'interest_rate' in col.lower() and 'base' in col]
        quote_rate_cols = [col for col in df.columns if 'interest_rate' in col.lower() and 'quote' in col]
        
        if base_rate_cols and quote_rate_cols:
            df['interest_rate_diff'] = df[base_rate_cols[0]] - df[quote_rate_cols[0]]
        else:
            df['interest_rate_diff'] = 0.0
        
        # Policy rate differential
        base_policy_cols = [col for col in df.columns if 'policy_rate' in col.lower() and 'base' in col]
        quote_policy_cols = [col for col in df.columns if 'policy_rate' in col.lower() and 'quote' in col]
        
        if base_policy_cols and quote_policy_cols:
            df['policy_rate_diff'] = df[base_policy_cols[0]] - df[quote_policy_cols[0]]
        else:
            df['policy_rate_diff'] = 0.0
        
        return df
    
    def _calculate_inflation_differential(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate inflation differential (base - quote)"""
        
        base_inflation_cols = [col for col in df.columns if 'inflation' in col.lower() and 'base' in col]
        quote_inflation_cols = [col for col in df.columns if 'inflation' in col.lower() and 'quote' in col]
        
        if base_inflation_cols and quote_inflation_cols:
            df['inflation_diff'] = df[base_inflation_cols[0]] - df[quote_inflation_cols[0]]
        else:
            df['inflation_diff'] = 0.0
        
        return df
    
    def _calculate_surprise_metric(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate economic surprise: actual - forecast
        Positive = better than expected
        """
        
        # Look for forecast columns
        forecast_cols = [col for col in df.columns if 'forecast' in col.lower()]
        value_cols = [col for col in df.columns if col.startswith('value_') and 'base' in col]
        
        if forecast_cols and value_cols:
            # Calculate surprise for key indicators
            surprises = []
            for i, row in df.iterrows():
                total_surprise = 0
                count = 0
                
                for val_col in value_cols:
                    # Find corresponding forecast column
                    series_id = val_col.replace('value_', '').replace('_base', '')
                    forecast_col = f'forecast_value_{series_id}_base'
                    
                    if forecast_col in df.columns:
                        actual = row[val_col]
                        forecast = row[forecast_col]
                        
                        if pd.notna(actual) and pd.notna(forecast) and forecast != 0:
                            # Normalize surprise by forecast value
                            surprise = (actual - forecast) / abs(forecast)
                            total_surprise += surprise
                            count += 1
                
                avg_surprise = total_surprise / count if count > 0 else 0
                surprises.append(avg_surprise)
            
            df['surprise_metric'] = surprises
        else:
            df['surprise_metric'] = 0.0
        
        return df
    
    def _calculate_yield_spread(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate yield spread proxy
        Using government bond yields if available
        """
        
        base_yield_cols = [col for col in df.columns if 'yield' in col.lower() and 'base' in col]
        quote_yield_cols = [col for col in df.columns if 'yield' in col.lower() and 'quote' in col]
        
        if base_yield_cols and quote_yield_cols:
            df['yield_spread'] = df[base_yield_cols[0]] - df[quote_yield_cols[0]]
        else:
            # Use interest rate as proxy
            df['yield_spread'] = df.get('interest_rate_diff', 0.0)
        
        return df
    
    def _calculate_risk_sentiment(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate risk-on/risk-off proxy
        Using volatility indices, stock market performance
        Returns: -1 (risk-off) to +1 (risk-on)
        """
        
        # Look for VIX or similar volatility indices
        vix_cols = [col for col in df.columns if 'vix' in col.lower() or 'volatility' in col.lower()]
        
        if vix_cols:
            # Normalize VIX: low VIX = risk-on, high VIX = risk-off
            vix_values = df[vix_cols[0]]
            
            # Z-score normalization
            vix_mean = vix_values.mean()
            vix_std = vix_values.std()
            
            if vix_std > 0:
                vix_zscore = (vix_values - vix_mean) / vix_std
                # Invert and clip to [-1, 1]
                df['risk_sentiment'] = (-vix_zscore).clip(-1, 1)
            else:
                df['risk_sentiment'] = 0.0
        else:
            # Use stock market returns as proxy
            stock_cols = [col for col in df.columns if 'stock' in col.lower() or 'equity' in col.lower()]
            
            if stock_cols:
                returns = df[stock_cols[0]].pct_change()
                # Normalize returns
                returns_mean = returns.mean()
                returns_std = returns.std()
                
                if returns_std > 0:
                    returns_zscore = (returns - returns_mean) / returns_std
                    df['risk_sentiment'] = returns_zscore.clip(-1, 1)
                else:
                    df['risk_sentiment'] = 0.0
            else:
                df['risk_sentiment'] = 0.0
        
        return df
    
    def _calculate_gdp_growth_differential(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate GDP growth differential"""
        
        base_gdp_cols = [col for col in df.columns if 'gdp' in col.lower() and 'base' in col]
        quote_gdp_cols = [col for col in df.columns if 'gdp' in col.lower() and 'quote' in col]
        
        if base_gdp_cols and quote_gdp_cols:
            df['gdp_growth_diff'] = df[base_gdp_cols[0]] - df[quote_gdp_cols[0]]
        else:
            df['gdp_growth_diff'] = 0.0
        
        return df
    
    def _save_features(self, df: pd.DataFrame):
        """Save calculated features to database"""
        
        features_to_create = []
        
        for _, row in df.iterrows():
            if pd.notna(row['date']):
                features_to_create.append(
                    MacroFeatures(
                        currency_pair=self.currency_pair,
                        date=row['date'],
                        interest_rate_diff=row.get('interest_rate_diff'),
                        policy_rate_diff=row.get('policy_rate_diff'),
                        inflation_diff=row.get('inflation_diff'),
                        surprise_metric=row.get('surprise_metric'),
                        yield_spread=row.get('yield_spread'),
                        risk_sentiment=row.get('risk_sentiment'),
                        gdp_growth_diff=row.get('gdp_growth_diff')
                    )
                )
        
        # Bulk insert
        MacroFeatures.objects.bulk_create(
            features_to_create,
            batch_size=1000,
            ignore_conflicts=True
        )
