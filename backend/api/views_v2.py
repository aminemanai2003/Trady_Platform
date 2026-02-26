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
            "symbol": "EURUSD",
            "base_currency": "EUR",
            "quote_currency": "USD"
        }
        
        Returns full breakdown:
        - Final signal
        - Individual agent signals
        - Weights used
        - Safety checks
        - Explanations
        """
        symbol = request.data.get('symbol', 'EURUSD')
        base = request.data.get('base_currency', 'EUR')
        quote = request.data.get('quote_currency', 'USD')
        
        # Safety check
        safety_check = self.safety_monitor.should_allow_signal(symbol)
        
        if not safety_check['allowed']:
            return Response({
                'signal_generated': False,
                'reason': safety_check['reason'],
                'safety_checks': safety_check
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Generate signal
        try:
            result = self.coordinator.generate_final_signal(symbol, base, quote)
            
            return Response({
                'success': True,
                'signal': result['final_signal'],
                'confidence': result['confidence'],
                'agent_breakdown': {
                    agent: {
                        'signal': data['signal'],
                        'confidence': data['confidence'],
                        'reason': data['deterministic_reason']
                    }
                    for agent, data in result['agent_signals'].items()
                },
                'weights_used': result['weights_used'],
                'market_regime': result['market_regime'],
                'conflicts_detected': result['conflicts_detected'],
                'explanation': result['explanation'],
                'timestamp': result['timestamp'],
                'safety_checks': safety_check
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
        
        performance = self.perf_tracker.get_all_agents_performance(days)
        
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
        # Check if any agents should be disabled
        disable_checks = {
            agent: self.perf_tracker.should_disable_agent(agent)
            for agent in ['TechnicalV2', 'MacroV2', 'SentimentV2']
        }
        
        circuit_breaker = self.safety_monitor.check_circuit_breaker()
        drift = self.drift_detector.get_drift_summary()
        
        system_healthy = (
            not circuit_breaker['triggered'] and
            not drift['sentiment']['drift_detected'] and
            not any(disable_checks.values())
        )
        
        return Response({
            'system_healthy': system_healthy,
            'circuit_breaker': circuit_breaker,
            'drift_detection': drift,
            'agent_disable_checks': disable_checks,
            'timestamp': datetime.now().isoformat()
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
        
        # Would query database for signal details
        # Return full breakdown with feature values
        
        return Response({
            'signal_id': signal_id,
            'explanation': 'Detailed breakdown of signal logic',
            'features_used': {},
            'decision_tree': []
        })
