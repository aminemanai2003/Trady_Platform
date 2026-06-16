import unittest
from unittest.mock import Mock

import numpy as np
import pandas as pd

from decision_layer.xai_formatter import XAIFormatter
from decision_layer.llm_tool_judge import LLMToolJudge
from data_layer.news_loader import NewsLoader
from signal_layer.coordinator_agent_v2 import CoordinatorAgentV2
from signal_layer.technical_agent_v2 import TechnicalAgentV2
from signal_layer.sentiment_agent_v2 import SentimentAgentV2


class TestTechnicalEvidence(unittest.TestCase):
    def test_builds_aligned_timeframes_from_hourly_data(self):
        periods = 24 * 365
        index = pd.date_range("2025-01-01", periods=periods, freq="h")
        prices = np.linspace(1.05, 1.15, periods)
        hourly = pd.DataFrame({
            "timestamp": index,
            "open": prices,
            "high": prices + 0.001,
            "low": prices - 0.001,
            "close": prices + 0.0002,
            "volume": np.full(periods, 100.0),
        })

        frames = TechnicalAgentV2._build_timeframes(hourly)

        self.assertEqual(set(frames), {"1h", "4h", "1d"})
        self.assertEqual(len(frames["1h"]), periods)
        self.assertGreaterEqual(len(frames["4h"]), 200)
        self.assertGreaterEqual(len(frames["1d"]), 300)


class TestEvidenceWeighting(unittest.TestCase):
    def setUp(self):
        self.coordinator = CoordinatorAgentV2.__new__(CoordinatorAgentV2)
        self.coordinator.agent_weights = {
            "TechnicalV2": 0.35,
            "MacroV2": 0.25,
            "SentimentV2": 0.20,
            "GeopoliticalV2": 0.20,
        }
        tracker = Mock()
        tracker.get_agent_performance.return_value = {
            "trade_count": 0,
            "sharpe_ratio": 0.0,
        }
        self.coordinator.performance_tracker = tracker

    def test_low_quality_evidence_loses_voting_power(self):
        signals = {
            "TechnicalV2": {"data_quality": 1.0},
            "MacroV2": {"data_quality": 1.0},
            "SentimentV2": {"data_quality": 0.25},
            "GeopoliticalV2": {"data_quality": 0.0},
        }

        weights, metadata = self.coordinator._calculate_dynamic_weights(signals)

        self.assertAlmostEqual(sum(weights.values()), 1.0)
        self.assertEqual(weights["GeopoliticalV2"], 0.0)
        self.assertLess(weights["SentimentV2"], weights["MacroV2"])
        self.assertEqual(metadata["method"], "default_priors")
        self.assertLess(metadata["evidence_coverage"], 1.0)

    def test_performance_learning_requires_minimum_sample_for_every_agent(self):
        self.coordinator.performance_tracker.get_agent_performance.side_effect = [
            {"trade_count": 20, "sharpe_ratio": 1.5},
            {"trade_count": 20, "sharpe_ratio": 0.5},
            {"trade_count": 20, "sharpe_ratio": 0.2},
            {"trade_count": 2, "sharpe_ratio": 2.0},
        ]
        signals = {
            name: {"data_quality": 1.0}
            for name in self.coordinator.agent_weights
        }

        weights, metadata = self.coordinator._calculate_dynamic_weights(signals)

        self.assertEqual(metadata["method"], "default_priors")
        self.assertEqual(weights, self.coordinator.agent_weights)

    def test_correlation_checks_partner_direction(self):
        engine = Mock()
        engine.get_correlation_signals.return_value = {
            "correlation_matrix": {
                "EURUSD": {
                    "EURUSD": 1.0,
                    "GBPUSD": 0.8,
                    "USDCHF": -0.7,
                }
            },
            "pair_momentum": {
                "GBPUSD": 0.01,
                "USDCHF": -0.01,
            },
        }
        self.coordinator.correlation_engine = engine

        result = self.coordinator._validate_with_correlations(
            "EURUSD",
            signal=1,
            confidence=0.5,
        )

        self.assertEqual(result["aligned_pairs"], 2)
        self.assertEqual(result["conflicting_pairs"], 0)
        self.assertGreater(result["adjusted_confidence"], 0.5)


class TestExplanationAlignment(unittest.TestCase):
    def test_contribution_includes_confidence(self):
        formatter = XAIFormatter()
        breakdown = formatter._build_agent_breakdown({
            "agent_signals": {
                "TechnicalV2": {
                    "signal": 1,
                    "confidence": 0.5,
                    "features_used": {},
                    "data_quality": 0.8,
                    "evidence_count": 3,
                }
            },
            "weights_used": {"TechnicalV2": 0.4},
        })

        self.assertEqual(breakdown["TechnicalV2"]["contribution"], 0.2)
        self.assertEqual(breakdown["TechnicalV2"]["data_quality"], 0.8)
        self.assertEqual(breakdown["TechnicalV2"]["evidence_count"], 3)


class TestPairSpecificNews(unittest.TestCase):
    def test_untagged_article_requires_currency_text_match(self):
        article = {
            "title": "Bank of Japan discusses policy normalization",
            "content": "The yen moved after the BOJ statement.",
            "currencies": [],
        }

        self.assertTrue(NewsLoader._row_matches_currencies(article, {"JPY"}))
        self.assertFalse(NewsLoader._row_matches_currencies(article, {"EUR"}))

    def test_sentiment_currency_match_uses_tags_or_text(self):
        tagged = pd.Series({
            "title": "Markets update",
            "content": "",
            "currencies": ["USD"],
        })
        textual = pd.Series({
            "title": "ECB keeps policy unchanged",
            "content": "Eurozone investors react.",
            "currencies": [],
        })

        self.assertTrue(SentimentAgentV2._mentions_currency(tagged, "USD"))
        self.assertTrue(SentimentAgentV2._mentions_currency(textual, "EUR"))
        self.assertFalse(SentimentAgentV2._mentions_currency(textual, "JPY"))


class TestAdvisoryGuardrails(unittest.TestCase):
    def setUp(self):
        self.judge = LLMToolJudge.__new__(LLMToolJudge)

    def test_same_direction_confidence_difference_is_not_a_conflict(self):
        review = {
            "risk_flags": [],
            "inconsistencies": [
                "Conflicting signal directions because SELL confidences differ."
            ],
            "reasoning": "There is a signal direction conflict.",
        }
        tool_input = {
            "coordinator_confidence": 0.52,
            "agents": {
                "TechnicalV2": {"signal": -1},
                "MacroV2": {"signal": -1},
            },
            "actuarial": {"expected_value_pips": 0.3},
            "evidence": {"coverage": 0.7},
        }

        result = self.judge._enforce_objective_checks(review, tool_input)

        self.assertEqual(result["inconsistencies"], [])
        self.assertIn("LOW_CONFIDENCE", result["risk_flags"])
        self.assertIn("LOW_EVIDENCE", result["risk_flags"])
        self.assertNotIn("AGENT_DIVERGENCE", result["risk_flags"])

    def test_opposing_directions_are_flagged(self):
        review = {"risk_flags": [], "inconsistencies": [], "reasoning": ""}
        tool_input = {
            "coordinator_confidence": 0.7,
            "agents": {
                "TechnicalV2": {"signal": 1},
                "MacroV2": {"signal": -1},
            },
            "actuarial": {"expected_value_pips": -1.0},
            "evidence": {"coverage": 1.0},
        }

        result = self.judge._enforce_objective_checks(review, tool_input)

        self.assertIn("AGENT_DIVERGENCE", result["risk_flags"])
        self.assertIn("NEGATIVE_EV", result["risk_flags"])
        self.assertTrue(result["inconsistencies"])


if __name__ == "__main__":
    unittest.main()
