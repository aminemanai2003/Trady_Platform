"""
Unit Tests for Decision Layer Components
Tests ActuarialScorer, LLMJudge, RiskManager, XAIFormatter, Pipeline
"""
import unittest
from unittest.mock import Mock, patch
from datetime import datetime

# Import modules to test
from decision_layer.actuarial_scorer import ActuarialScorer
from decision_layer.llm_judge import LLMJudge
from decision_layer.xai_formatter import XAIFormatter
from risk.risk_manager import RiskManager
from risk.position_sizer import PositionSizer


class TestActuarialScorer(unittest.TestCase):
    """Test ActuarialScorer calculations"""
    
    def setUp(self):
        self.scorer = ActuarialScorer()
    
    def test_calculate_ev_positive(self):
        """Test positive expected value calculation"""
        ev = self.scorer.calculate_ev(
            p_win=0.60,
            p_loss=0.40,
            avg_win=50,
            avg_loss=30
        )
        self.assertGreater(ev, 0)
        self.assertAlmostEqual(ev, 18.0, places=1)  # 0.6*50 - 0.4*30 = 18
    
    def test_calculate_ev_negative(self):
        """Test negative expected value calculation"""
        ev = self.scorer.calculate_ev(
            p_win=0.40,
            p_loss=0.60,
            avg_win=30,
            avg_loss=50
        )
        self.assertLess(ev, 0)
        self.assertAlmostEqual(ev, -18.0, places=1)  # 0.4*30 - 0.6*50 = -18
    
    def test_estimate_probabilities_high_confidence(self):
        """Test probability estimation with high confidence"""
        probs = self.scorer.estimate_probabilities(
            confidence=0.85,
            signal=1,
            base_win_rate=0.55
        )
        self.assertGreater(probs['p_win'], 0.55)
        self.assertAlmostEqual(probs['p_win'] + probs['p_loss'], 1.0, places=2)
    
    def test_estimate_probabilities_low_confidence(self):
        """Test probability estimation with low confidence"""
        probs = self.scorer.estimate_probabilities(
            confidence=0.30,
            signal=1,
            base_win_rate=0.55
        )
        self.assertLess(probs['p_win'], 0.55)
        self.assertAlmostEqual(probs['p_win'] + probs['p_loss'], 1.0, places=2)
    
    def test_calculate_risk_reward(self):
        """Test risk/reward ratio calculation"""
        rr = self.scorer.calculate_risk_reward(avg_win=60, avg_loss=40)
        self.assertAlmostEqual(rr, 1.5, places=2)
    
    def test_score_trade_positive_ev(self):
        """Test full trade scoring with positive EV"""
        coordinator_output = {
            'final_signal': 1,
            'confidence': 0.75
        }
        
        historical_stats = {
            'win_rate': 0.58,
            'avg_win_pips': 45,
            'avg_loss_pips': 30
        }
        
        scores = self.scorer.score_trade(coordinator_output, historical_stats)
        
        self.assertGreater(scores['expected_value_pips'], 0)
        self.assertEqual(scores['verdict'], 'TRADE')
        self.assertIn('probability_win', scores)
        self.assertIn('risk_reward_ratio', scores)


class TestRiskManager(unittest.TestCase):
    """Test RiskManager validation logic"""
    
    def setUp(self):
        self.risk_manager = RiskManager()
    
    def test_validate_trade_approved(self):
        """Test trade approval with good parameters"""
        result = self.risk_manager.validate_trade(
            signal=1,
            confidence=0.75,
            symbol='EURUSD',
            entry_price=1.1000,
            atr=0.0035,
            capital=10000.0,
            current_equity=10000.0,
            peak_equity=10000.0,
            current_positions=0,
            expected_value_pips=20.0,
            win_rate=0.58,
            avg_win=45,
            avg_loss=30
        )
        
        self.assertTrue(result['approved'])
        self.assertGreater(result['position_size'], 0)
        self.assertIsNotNone(result['stop_loss'])
        self.assertIsNotNone(result['take_profit'])
    
    def test_validate_trade_low_confidence_rejection(self):
        """Test trade rejection due to low confidence"""
        result = self.risk_manager.validate_trade(
            signal=1,
            confidence=0.35,  # Below 0.50 threshold
            symbol='EURUSD',
            entry_price=1.1000,
            atr=0.0035,
            capital=10000.0,
            current_equity=10000.0,
            peak_equity=10000.0,
            current_positions=0,
            expected_value_pips=20.0
        )
        
        self.assertFalse(result['approved'])
        self.assertIn('Confidence', result['reason'])
    
    def test_validate_trade_negative_ev_rejection(self):
        """Test trade rejection due to negative EV"""
        result = self.risk_manager.validate_trade(
            signal=1,
            confidence=0.75,
            symbol='EURUSD',
            entry_price=1.1000,
            atr=0.0035,
            capital=10000.0,
            current_equity=10000.0,
            peak_equity=10000.0,
            current_positions=0,
            expected_value_pips=-5.0  # Negative EV
        )
        
        self.assertFalse(result['approved'])
        self.assertIn('Expected value', result['reason'])
    
    def test_validate_trade_max_drawdown_rejection(self):
        """Test trade rejection due to max drawdown"""
        result = self.risk_manager.validate_trade(
            signal=1,
            confidence=0.75,
            symbol='EURUSD',
            entry_price=1.1000,
            atr=0.0035,
            capital=10000.0,
            current_equity=8000.0,  # -20% from peak
            peak_equity=10000.0,
            current_positions=0,
            expected_value_pips=20.0
        )
        
        self.assertFalse(result['approved'])
        self.assertIn('Drawdown', result['reason'])
    
    def test_validate_trade_max_positions_rejection(self):
        """Test trade rejection due to max concurrent positions"""
        result = self.risk_manager.validate_trade(
            signal=1,
            confidence=0.75,
            symbol='EURUSD',
            entry_price=1.1000,
            atr=0.0035,
            capital=10000.0,
            current_equity=10000.0,
            peak_equity=10000.0,
            current_positions=4,  # At max limit
            expected_value_pips=20.0
        )
        
        self.assertFalse(result['approved'])
        self.assertIn('concurrent positions', result['reason'])
    
    def test_calculate_drawdown(self):
        """Test drawdown calculation"""
        drawdown = self.risk_manager._calculate_drawdown(
            current_equity=8500.0,
            peak_equity=10000.0
        )
        self.assertAlmostEqual(drawdown, -15.0, places=1)


class TestPositionSizer(unittest.TestCase):
    """Test PositionSizer calculations"""
    
    def setUp(self):
        self.sizer = PositionSizer()
    
    def test_kelly_criterion_positive(self):
        """Test Kelly criterion with positive expectancy"""
        kelly = self.sizer.kelly_criterion(
            win_rate=0.60,
            avg_win=1.5,
            avg_loss=1.0
        )
        self.assertGreater(kelly, 0)
        self.assertLessEqual(kelly, 0.25)  # Half-Kelly max
    
    def test_kelly_criterion_zero_loss(self):
        """Test Kelly criterion with zero loss"""
        kelly = self.sizer.kelly_criterion(
            win_rate=0.60,
            avg_win=1.5,
            avg_loss=0.0
        )
        self.assertEqual(kelly, 0.0)  # Safety check
    
    def test_atr_based_size(self):
        """Test ATR-based position sizing"""
        size = self.sizer.atr_based_size(
            capital=10000.0,
            atr=0.0035,
            risk_pct=0.02
        )
        self.assertGreater(size, 0)
        self.assertLessEqual(size, 10.0)  # Max 10 lots
    
    def test_combined_size(self):
        """'Test combined position sizing"""
        result = self.sizer.combined_size(
            capital=10000.0,
            confidence=0.75,
            atr=0.0035,
            win_rate=0.58,
            avg_win=1.5,
            avg_loss=1.0
        )
        
        self.assertIn('lot_size', result)
        self.assertIn('stop_loss_pips', result)
        self.assertIn('take_profit_pips', result)
        self.assertGreater(result['lot_size'], 0)
    
    def test_calculate_stop_loss_buy(self):
        """Test stop-loss calculation for BUY"""
        sl = self.sizer.calculate_stop_loss(
            entry_price=1.1000,
            atr=0.0035,
            signal=1,  # BUY
            atr_multiplier=1.5
        )
        self.assertLess(sl, 1.1000)  # SL below entry for BUY
    
    def test_calculate_stop_loss_sell(self):
        """Test stop-loss calculation for SELL"""
        sl = self.sizer.calculate_stop_loss(
            entry_price=1.1000,
            atr=0.0035,
            signal=-1,  # SELL
            atr_multiplier=1.5
        )
        self.assertGreater(sl, 1.1000)  # SL above entry for SELL


class TestLLMJudge(unittest.TestCase):
    """Test LLMJudge decision logic"""
    
    def setUp(self):
        self.judge = LLMJudge()
    
    def test_quick_rejection_low_confidence(self):
        """Test quick rejection for low confidence"""
        coordinator_output = {
            'confidence': 0.35,
            'final_signal': 1,
            'conflicts_detected': False
        }
        actuarial_scores = {
            'expected_value_pips': 10.0
        }
        
        rejection = self.judge._quick_rejection_check(
            coordinator_output,
            actuarial_scores
        )
        
        self.assertIsNotNone(rejection)
        self.assertIn('Confidence', rejection)
    
    def test_quick_rejection_negative_ev(self):
        """Test quick rejection for negative EV"""
        coordinator_output = {
            'confidence': 0.75,
            'final_signal': 1,
            'conflicts_detected': False
        }
        actuarial_scores = {
            'expected_value_pips': -5.0
        }
        
        rejection = self.judge._quick_rejection_check(
            coordinator_output,
            actuarial_scores
        )
        
        self.assertIsNotNone(rejection)
        self.assertIn('expected value', rejection.lower())
    
    def test_quick_rejection_neutral_signal(self):
        """Test quick rejection for NEUTRAL signal"""
        coordinator_output = {
            'confidence': 0.75,
            'final_signal': 0,  # NEUTRAL
            'conflicts_detected': False
        }
        actuarial_scores = {
            'expected_value_pips': 10.0
        }
        
        rejection = self.judge._quick_rejection_check(
            coordinator_output,
            actuarial_scores
        )
        
        self.assertIsNotNone(rejection)
        self.assertIn('NEUTRAL', rejection)
    
    def test_parse_llm_response_approve(self):
        """Test parsing APPROVE response"""
        response = """VERDICT: APPROVE
REASON: Strong technical setup with macro support and positive expected value.
CONFIDENCE: 0.85"""
        
        parsed = self.judge._parse_llm_response(response)
        
        self.assertEqual(parsed['verdict'], 'APPROVE')
        self.assertIn('Strong technical', parsed['reasoning'])
    
    def test_parse_llm_response_reject(self):
        """Test parsing REJECT response"""
        response = """VERDICT: REJECT
REASON: Conflicting signals with low confidence below threshold.
CONFIDENCE: 0.47"""
        
        parsed = self.judge._parse_llm_response(response)
        
        self.assertEqual(parsed['verdict'], 'REJECT')
        self.assertIn('conflicting_signals', parsed['rejection_criteria'])


class TestXAIFormatter(unittest.TestCase):
    """Test XAI Formatter output structure"""
    
    def setUp(self):
        self.formatter = XAIFormatter()
    
    def test_format_approved_trade(self):
        """Test formatting for approved trade"""
        coordinator_output = {
            'final_signal': 1,
            'confidence': 0.85,
            'symbol': 'EURUSD',
            'agent_signals': {
                'TechnicalV2': {'signal': 1, 'confidence': 0.82, 'features_used': {}},
                'MacroV2': {'signal': 1, 'confidence': 0.78, 'features_used': {}},
                'SentimentV2': {'signal': 0, 'confidence': 0.55, 'features_used': {}}
            },
            'weights_used': {'TechnicalV2': 0.4, 'MacroV2': 0.35, 'SentimentV2': 0.25},
            'conflicts_detected': False,
            'market_regime': 'trending',
            'timestamp': datetime.now().isoformat()
        }
        
        actuarial_scores = {
            'expected_value_pips': 22.5,
            'probability_win': 0.68,
            'risk_reward_ratio': 1.75
        }
        
        judge_decision = {
            'verdict': 'APPROVE',
            'reasoning': 'Strong setup',
            'latency_ms': 420
        }
        
        risk_validation = {
            'approved': True,
            'reason': 'All parameters satisfied',
            'position_size': 0.5,
            'stop_loss': 1.0950,
            'take_profit': 1.1080,
            'violations': []
        }
        
        xai = self.formatter.format(
            coordinator_output,
            actuarial_scores,
            judge_decision,
            risk_validation
        )
        
        self.assertEqual(xai['decision'], 'APPROVED')
        self.assertIn('agent_breakdown', xai)
        self.assertIn('actuarial_metrics', xai)
        self.assertIn('judge_evaluation', xai)
        self.assertIn('risk_assessment', xai)
        self.assertIn('human_explanation', xai)


if __name__ == '__main__':
    unittest.main()
