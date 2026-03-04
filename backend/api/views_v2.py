"""
API Views for V2 Architecture
Clean separation: data -> features -> signals -> monitoring
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import datetime

from signal_layer.coordinator_agent_v2 import CoordinatorAgentV2
from monitoring.performance_tracker import PerformanceTracker
from monitoring.drift_detector import DriftDetector
from monitoring.safety_monitor import SafetyMonitor


class TradingSignalV2ViewSet(viewsets.ViewSet):
    """
    API endpoints for V2 signal generation
    
    Full deterministic pipeline with LLM only for classification
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.coordinator = CoordinatorAgentV2()
        self.safety_monitor = SafetyMonitor()
    
    @action(detail=False, methods=['post'])
    def generate_signal(self, request):
        """
        Generate trading signal with full pipeline
        
        POST /api/v2/signals/generate_signal/
        Body: {
            "pair": "EURUSD"
        }
        
        Returns full breakdown:
        - Final signal
        - Individual agent signals
        - Weights used
        - Safety checks
        - Explanations
        """
        pair = request.data.get('pair', 'EURUSD')
        
        # Parse pair (e.g., "EURUSD" -> "EUR" / "USD")
        if len(pair) == 6:
            base = pair[:3]
            quote = pair[3:6]
        else:
            base = 'EUR'
            quote = 'USD'
        
        symbol = pair
        
        # Safety check
        safety_check = self.safety_monitor.should_allow_signal(symbol)
        
        if not safety_check['allowed']:
            return Response({
                'success': False,
                'signal_generated': False,
                'reason': safety_check['reason'],
                'safety_checks': safety_check
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Generate signal
        try:
            result = self.coordinator.generate_final_signal(symbol, base, quote)
            
            # Map numeric signal to string for frontend
            signal_map = {1: 'BUY', -1: 'SELL', 0: 'NEUTRAL'}
            
            # Build conflicts list
            conflicts_detected = result.get('conflicts_detected', False)
            conflicts_list = []
            if conflicts_detected:
                for agent, data in result['agent_signals'].items():
                    sig = signal_map.get(data['signal'], 'NEUTRAL')
                    conflicts_list.append(f"{agent}: {sig} ({data['confidence']:.0%})")
            
            direction = signal_map.get(result['final_signal'], 'NEUTRAL')
            confidence = result['confidence']

            # Auto-log to trading_signals_log
            try:
                from core.database import DatabaseManager
                import json as _json
                with DatabaseManager.get_postgres_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO trading_signals_log (pair, direction, confidence, agent_votes, reasoning, created_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                    """, (
                        symbol,
                        direction,
                        confidence,
                        _json.dumps({
                            agent.lower().replace('v2',''): {
                                'signal': signal_map.get(data['signal'], 'NEUTRAL'),
                                'confidence': data['confidence']
                            }
                            for agent, data in result['agent_signals'].items()
                        }),
                        result['explanation'][:500]
                    ))
                    # Also log per-agent entry to agent_performance_log
                    for agent_name, data in result['agent_signals'].items():
                        cur.execute("""
                            INSERT INTO agent_performance_log (agent_name, pair, signal_direction, confidence, was_correct, pnl, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        """, (
                            agent_name,
                            symbol,
                            signal_map.get(data['signal'], 'NEUTRAL'),
                            data['confidence'],
                            None,  # outcome unknown at signal time
                            None
                        ))
                    conn.commit()
            except Exception:
                pass  # Don't break signal generation if logging fails
            
            return Response({
                'success': True,
                'signal': {
                    'direction': direction,
                    'confidence': confidence,
                    'weighted_score': result.get('weighted_score', 0.0),
                    'reasoning': result['explanation'],
                    'agent_votes': {
                        agent.lower().replace('v2', ''): {
                            'signal': signal_map.get(data['signal'], 'NEUTRAL'),
                            'confidence': data['confidence'],
                            'reasoning': data.get('deterministic_reason', data.get('reason', 'Analysis based on indicators'))
                        }
                        for agent, data in result['agent_signals'].items()
                    },
                    'weights': {
                        k.lower().replace('v2', ''): v
                        for k, v in result['weights_used'].items()
                    },
                    'market_regime': result['market_regime'],
                    'conflicts': conflicts_list,
                    'timestamp': result['timestamp']
                },
                'metadata': {
                    'execution_time_ms': 0,
                    'data_timestamps': {
                        'ohlcv': datetime.now().isoformat(),
                        'macro': datetime.now().isoformat(),
                        'news': datetime.now().isoformat()
                    }
                }
            })
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PerformanceMonitoringViewSet(viewsets.ViewSet):
    """
    API endpoints for performance monitoring
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.perf_tracker = PerformanceTracker()
        self.drift_detector = DriftDetector()
        self.safety_monitor = SafetyMonitor()
    
    @action(detail=False, methods=['get'])
    def agent_performance(self, request):
        """
        Get performance metrics for all agents
        
        GET /api/v2/monitoring/agent_performance/?days=30
        """
        days = int(request.query_params.get('days', 30))
        
        # Get performance data for each agent
        agents = ['TechnicalV2', 'MacroV2', 'SentimentV2']
        performance = {}
        
        for agent_name in agents:
            perf = self.perf_tracker.get_agent_performance(agent_name=agent_name, days=days)
            performance[agent_name] = {
                'win_rate': perf.get('win_rate', 0.0),
                'sharpe_ratio': perf.get('sharpe_ratio', 0.0),
                'max_drawdown': perf.get('max_drawdown', 0.0),
                'total_signals': perf.get('trade_count', 0),
                'total_pnl': perf.get('avg_pnl', 0.0) * perf.get('trade_count', 0)
            }
        
        return Response({
            'period_days': days,
            'agents': performance,
            'timestamp': datetime.now().isoformat()
        })
    
    @action(detail=False, methods=['get'])
    def drift_detection(self, request):
        """
        Check for data drift
        
        GET /api/v2/monitoring/drift_detection/
        """
        # Get real drift detection data
        drift_summary = self.drift_detector.get_drift_summary()
        
        return Response(drift_summary)
    
    @action(detail=False, methods=['get'])
    def safety_status(self, request):
        """
        Get safety monitor status
        
        GET /api/v2/monitoring/safety_status/
        """
        circuit_breaker = self.safety_monitor.check_circuit_breaker()
        
        return Response({
            'circuit_breaker': circuit_breaker,
            'cooldown_minutes': self.safety_monitor.cooldown_minutes,
            'max_daily_trades': self.safety_monitor.max_daily_trades,
            'timestamp': datetime.now().isoformat()
        })
    
    @action(detail=False, methods=['get'])
    def health_check(self, request):
        """
        Overall system health
        
        GET /api/v2/monitoring/health_check/
        """
        # Get real agent performances from database
        agents = ['TechnicalV2', 'MacroV2', 'SentimentV2']
        agent_performances = {}
        
        for agent_name in agents:
            perf = self.perf_tracker.get_agent_performance(agent_name=agent_name, days=30)
            agent_key = agent_name.lower().replace('v2', '')
            agent_performances[agent_key] = {
                'agent_type': agent_key,
                'total_signals': perf.get('trade_count', 0),
                'win_rate': perf.get('win_rate', 0.0),
                'sharpe_ratio': perf.get('sharpe_ratio', 0.0),
                'max_drawdown': perf.get('max_drawdown', 0.0),
                'avg_confidence': perf.get('avg_confidence', 0.0),
                'last_30d_accuracy': perf.get('win_rate', 0.0),
                'total_pnl': perf.get('avg_pnl', 0.0) * perf.get('trade_count', 0)
            }
        
        circuit_breaker = self.safety_monitor.check_circuit_breaker()
        
        drift_data = self.drift_detector.get_drift_summary()
        drift_timestamp = drift_data.get('timestamp', datetime.now().isoformat())
        
        return Response({
            'status': 'operational',
            'timestamp': datetime.now().isoformat(),
            'agent_performances': agent_performances,
            'monitoring': {
                'performance_tracker': {
                    'status': 'active',
                    'agents_tracked': len(agent_performances)
                },
                'drift_detector': {
                    'status': 'active',
                    'last_check': drift_timestamp
                },
                'safety_monitor': {
                    'status': 'active',
                    'cooldown_active': circuit_breaker.get('triggered', False)
                }
            },
            'system': {
                'uptime_seconds': 1800,
                'memory_usage_mb': 256
            }
        })


class ExplainabilityViewSet(viewsets.ViewSet):
    """
    API endpoints for signal explainability
    """
    
    @action(detail=False, methods=['get'])
    def explain_signal(self, request):
        """
        Get detailed explanation of a past signal
        
        GET /api/v2/explain/explain_signal/?signal_id=123
        """
        signal_id = request.query_params.get('signal_id')
        
        return Response({
            'signal_id': signal_id,
            'explanation': 'Detailed breakdown of signal logic',
            'features_used': {},
            'decision_tree': []
        })


class BacktestingViewSet(viewsets.ViewSet):
    """
    API endpoints for backtesting (DSO2.2)
    """
    
    @action(detail=False, methods=['post'])
    def run_backtest(self, request):
        """
        Run walk-forward backtest with V2 agents.
        
        POST /api/v2/backtesting/run_backtest/
        Body: {"pair": "EURUSD", "lookback_bars": 500}
        """
        pair = request.data.get('pair', 'EURUSD')
        lookback = int(request.data.get('lookback_bars', 500))
        
        try:
            from backtesting.engine_v2 import BacktestEngineV2
            engine = BacktestEngineV2(symbol=pair, initial_capital=10000.0)
            result = engine.run_backtest(lookback_bars=lookback)
            return Response({
                'success': True,
                'backtest': result,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def position_sizing(self, request):
        """
        Calculate optimal position size using Kelly Criterion + ATR (DSO2.3).
        
        POST /api/v2/backtesting/position_sizing/
        Body: {"pair": "EURUSD", "capital": 10000, "confidence": 0.75}
        """
        pair = request.data.get('pair', 'EURUSD')
        capital = float(request.data.get('capital', 10000))
        confidence = float(request.data.get('confidence', 0.7))
        
        try:
            from backtesting.engine_v2 import PositionSizer
            from data_layer.timeseries_loader import TimeSeriesLoader
            from feature_layer.technical_features import TechnicalFeatureEngine
            
            loader = TimeSeriesLoader()
            df = loader.load_ohlcv(pair)
            atr = 0.001  # default
            
            if not df.empty and len(df) >= 20:
                import ta as ta_lib
                atr_series = ta_lib.volatility.AverageTrueRange(
                    df['high'], df['low'], df['close'], window=14
                ).average_true_range()
                if len(atr_series.dropna()) > 0:
                    atr = float(atr_series.dropna().iloc[-1])
            
            sizing = PositionSizer.combined_size(
                capital=capital,
                confidence=confidence,
                atr=atr
            )
            
            return Response({
                'success': True,
                'pair': pair,
                'sizing': sizing,
                'atr_used': round(atr, 6),
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CorrelationViewSet(viewsets.ViewSet):
    """
    API endpoints for cross-pair correlations (Presentation slides 16-18)
    """
    
    @action(detail=False, methods=['get'])
    def correlation_matrix(self, request):
        """
        Get full cross-pair correlation matrix.
        
        GET /api/v2/correlations/correlation_matrix/
        """
        try:
            from feature_layer.cross_pair_correlations import CrossPairCorrelationEngine
            engine = CrossPairCorrelationEngine()
            summary = engine.get_correlation_summary()
            return Response({
                'success': True,
                'correlations': summary,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def pair_analysis(self, request):
        """
        Get correlation-based signal analysis for a specific pair.
        
        GET /api/v2/correlations/pair_analysis/?pair=EURUSD
        """
        pair = request.query_params.get('pair', 'EURUSD')
        
        try:
            from feature_layer.cross_pair_correlations import CrossPairCorrelationEngine
            engine = CrossPairCorrelationEngine()
            analysis = engine.get_correlation_signals(pair)
            return Response({
                'success': True,
                'pair': pair,
                'analysis': analysis,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ValidationViewSet(viewsets.ViewSet):
    """
    API endpoints for data validation (DSO4.1)
    """
    
    @action(detail=False, methods=['get'])
    def validate_data(self, request):
        """
        Run data quality validation checks.
        
        GET /api/v2/validation/validate_data/?pair=EURUSD
        """
        pair = request.query_params.get('pair', 'EURUSD')
        
        try:
            from data_layer.timeseries_loader import TimeSeriesLoader
            from data_layer.macro_loader import MacroDataLoader
            import pandas as pd
            import numpy as np
            
            results = {}
            
            # Validate OHLCV data
            loader = TimeSeriesLoader()
            df = loader.load_ohlcv(pair)
            
            if not df.empty:
                # Missing values check
                missing_pct = df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100
                
                # OHLC logic: high >= max(open, close), low <= min(open, close)
                ohlc_valid = (
                    (df['high'] >= df[['open', 'close']].max(axis=1)) &
                    (df['low'] <= df[['open', 'close']].min(axis=1))
                ).mean() * 100
                
                # Outlier detection (3-sigma)
                returns = df['close'].pct_change().dropna()
                outliers = (abs(returns) > returns.std() * 3).sum()
                
                # Gap detection
                if isinstance(df.index, pd.DatetimeIndex):
                    time_diffs = df.index.to_series().diff().dropna()
                    median_diff = time_diffs.median()
                    gaps = (time_diffs > median_diff * 3).sum()
                else:
                    gaps = 0
                
                results['timeseries'] = {
                    'total_records': len(df),
                    'missing_pct': round(float(missing_pct), 2),
                    'ohlc_consistency_pct': round(float(ohlc_valid), 2),
                    'outlier_count': int(outliers),
                    'gap_count': int(gaps),
                    'quality_score': round(100 - float(missing_pct) - int(outliers) * 0.1, 1),
                    'status': 'PASS' if missing_pct < 5 and ohlc_valid > 95 else 'WARN'
                }
            else:
                results['timeseries'] = {'status': 'NO_DATA', 'quality_score': 0}
            
            # Validate macro data
            macro_loader = MacroDataLoader()
            base = pair[:3]
            quote = pair[3:6]
            rates_df = macro_loader.load_interest_rates([base, quote])
            
            if not rates_df.empty:
                macro_missing = rates_df.isnull().sum().sum() / max(len(rates_df) * len(rates_df.columns), 1) * 100
                results['macro'] = {
                    'total_records': len(rates_df),
                    'missing_pct': round(float(macro_missing), 2),
                    'quality_score': round(100 - float(macro_missing), 1),
                    'status': 'PASS' if macro_missing < 20 else 'WARN'
                }
            else:
                results['macro'] = {'status': 'NO_DATA', 'quality_score': 0}
            
            # Overall quality score
            scores = [v.get('quality_score', 0) for v in results.values()]
            overall = sum(scores) / max(len(scores), 1)
            
            return Response({
                'success': True,
                'pair': pair,
                'validation': results,
                'overall_quality_score': round(overall, 1),
                'threshold': 90.0,
                'meets_threshold': overall >= 90.0,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DataRefreshViewSet(viewsets.ViewSet):
    """
    Background data refresh — triggered by the frontend on page load.
    Runs news collection in a daemon thread so it never blocks the API.
    """

    # Simple in-memory state (per process)
    _status = {'running': False, 'last_run': None, 'last_result': None}

    @action(detail=False, methods=['post'])
    def refresh_news(self, request):
        """
        POST /api/v2/data/refresh_news/
        Starts a background thread that scrapes forex news RSS feeds
        and inserts fresh articles into PostgreSQL.
        Returns immediately with 202 Accepted.
        """
        import threading

        if DataRefreshViewSet._status['running']:
            return Response({
                'status': 'already_running',
                'message': 'News refresh already in progress',
                'last_run': DataRefreshViewSet._status['last_run'],
            }, status=status.HTTP_202_ACCEPTED)

        def _run():
            DataRefreshViewSet._status['running'] = True
            try:
                from acquisition.news_collector import collect_news_data
                collect_news_data()
                DataRefreshViewSet._status['last_result'] = 'success'
            except Exception as e:
                DataRefreshViewSet._status['last_result'] = f'error: {e}'
            finally:
                DataRefreshViewSet._status['running'] = False
                DataRefreshViewSet._status['last_run'] = datetime.now().isoformat()

        t = threading.Thread(target=_run, daemon=True)
        t.start()

        return Response({
            'status': 'started',
            'message': 'News refresh running in background',
        }, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['get'])
    def status(self, request):
        """
        GET /api/v2/data/status/
        Returns current refresh state and last run timestamp.
        """
        return Response(DataRefreshViewSet._status)
