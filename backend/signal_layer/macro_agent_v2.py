"""
Macro Agent V2 - DETERMINISTIC ONLY
NO LLM for trading logic
"""
from typing import Dict, List
from data_layer.macro_loader import MacroDataLoader
from feature_layer.macro_features import MacroFeatureEngine


class MacroAgentV2:
    """
    Macro Analysis Agent - Pure deterministic logic
    
    Uses:
    - Interest rate differentials
    - Inflation differentials
    - Rate momentum
    - Carry trade scores
    
    NO LLM - Only economic math
    """
    
    def __init__(self):
        self.data_loader = MacroDataLoader()
        self.feature_engine = MacroFeatureEngine()
    
    def generate_signal(
        self,
        base_currency: str,
        quote_currency: str,
        price_volatility: float = None
    ) -> Dict:
        """
        Generate macro signal using PURE LOGIC
        
        Returns:
            {
                'signal': -1/0/1,
                'confidence': 0-1,
                'features_used': dict,
                'deterministic_reason': str
            }
        """
        currencies = [base_currency, quote_currency]
        
        # Load data
        rates_df = self.data_loader.load_interest_rates(currencies)
        inflation_df = self.data_loader.load_inflation_rates(currencies)
        
        if rates_df.empty:
            return self._neutral_signal("No macro data available")

        rate_currencies = set(rates_df["currency"].dropna().astype(str))
        if not set(currencies).issubset(rate_currencies):
            missing = sorted(set(currencies) - rate_currencies)
            return self._neutral_signal(
                f"Incomplete interest-rate coverage for {', '.join(missing)}"
            )
        
        # Calculate features
        rate_diff = self.feature_engine.calculate_rate_differentials(
            rates_df, base_currency, quote_currency
        )
        
        inflation_diff = self.feature_engine.calculate_inflation_differential(
            inflation_df, base_currency, quote_currency
        )
        
        base_momentum = self.feature_engine.calculate_macro_momentum(
            rates_df, inflation_df, base_currency
        )
        
        # Carry score (needs volatility)
        carry_score = 0.0
        if price_volatility:
            carry_score = self.feature_engine.calculate_carry_score(
                rate_diff, price_volatility
            )
        
        # DETERMINISTIC signal generation
        result = self.feature_engine.get_macro_signal(
            rate_diff,
            inflation_diff,
            base_momentum['rate_momentum'],
            carry_score
        )
        inflation_currencies = set(inflation_df["currency"].dropna().astype(str))
        complete_inflation = set(currencies).issubset(inflation_currencies)
        result["data_quality"] = 1.0 if complete_inflation else 0.7
        result["evidence_count"] = len(rate_currencies) + len(inflation_currencies)
        result["agent"] = "MacroV2"
        return result
    
    def _neutral_signal(self, reason: str) -> Dict:
        """Return neutral signal"""
        return {
            'signal': 0,
            'confidence': 0.0,
            'features_used': {},
            'deterministic_reason': reason,
            'data_quality': 0.0,
            'evidence_count': 0,
            'agent': 'MacroV2'
        }
