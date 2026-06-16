"""
PHASE 6: Django REST API Views
All endpoints with clean service layer separation
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, timedelta

from api.serializers import (
    AgentSignalSerializer, CoordinatorDecisionSerializer,
    AgentPerformanceSerializer, BacktestRunSerializer,
    ValidationReportSerializer, DataQualityMetricSerializer
)
from agents.models import AgentSignal, CoordinatorDecision, AgentPerformance
from backtesting.models import BacktestRun
from validation.models import ValidationReport, DataQualityMetric

# Service imports
from agents.coordinator import CoordinatorAgent
from backtesting.engine import BacktestEngine
from validation.timeseries_validator import TimeSeriesValidator
from validation.macro_validator import MacroDataValidator
from validation.news_preprocessor import NewsPreprocessor
from features.technical_calculator import TechnicalFeaturesCalculator
from features.macro_calculator import MacroFeaturesCalculator
from features.sentiment_calculator import SentimentFeaturesCalculator


class SignalViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoints for trading signals
    GET /api/signals/latest/ - Get latest signal
    GET /api/signals/history/ - Get signal history
    """
    
    queryset = CoordinatorDecision.objects.all()
    serializer_class = CoordinatorDecisionSerializer
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Get latest trading signal for a symbol"""
        
        symbol = request.query_params.get('symbol', 'EURUSD')
        
        latest_decision = CoordinatorDecision.objects.filter(
            symbol=symbol
        ).order_by('-timestamp').first()
        
        if not latest_decision:
            return Response({
                'error': f'No signals found for {symbol}'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(latest_decision)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get signal history for a symbol"""
        
        symbol = request.query_params.get('symbol', 'EURUSD')
        limit = int(request.query_params.get('limit', 50))
        
        decisions = CoordinatorDecision.objects.filter(
            symbol=symbol
        ).order_by('-timestamp')[:limit]
        
        serializer = self.get_serializer(decisions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate a new signal (force refresh)"""
        
        symbol = request.data.get('symbol', 'EURUSD')
        
        try:
            coordinator = CoordinatorAgent()
            result = coordinator.make_decision(symbol)
            
            return Response({
                'status': 'success',
                'decision': result
            })
        
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AgentExplanationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoints for agent explanations
    GET /api/agent/explanations/ - Get agent reasoning
    """
    
    queryset = AgentSignal.objects.all()
    serializer_class = AgentSignalSerializer
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Get latest explanations from all agents"""
        
        symbol = request.query_params.get('symbol', 'EURUSD')
        
        explanations = {}
        
        for agent_type in ['technical', 'macro', 'sentiment']:
            signal = AgentSignal.objects.filter(
                agent_type=agent_type,
                symbol=symbol
            ).order_by('-timestamp').first()
            
            if signal:
                explanations[agent_type] = {
                    'signal': signal.signal,
                    'confidence': signal.confidence,
                    'reasoning': signal.reasoning,
                    'timestamp': signal.timestamp.isoformat()
                }
        
        return Response(explanations)


class BacktestViewSet(viewsets.ModelViewSet):
    """
    API endpoints for backtesting
    POST /api/backtest/run/ - Run a new backtest
    GET /api/backtest/results/ - Get backtest results
    """
    
    queryset = BacktestRun.objects.all()
    serializer_class = BacktestRunSerializer
    
    @action(detail=False, methods=['post'])
    def run(self, request):
        """Run a new backtest"""
        
        symbol = request.data.get('symbol', 'EURUSD')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        name = request.data.get('name', f'Backtest {symbol}')
        
        if not start_date or not end_date:
            return Response({
                'error': 'start_date and end_date are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Parse dates
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
            # Run backtest asynchronously (in production, use Celery)
            engine = BacktestEngine(symbol, start_dt, end_dt)
            result = engine.run(name=name)
            
            return Response({
                'status': 'success',
                'backtest_id': result['backtest_id'],
                'metrics': result['metrics']
            })
        
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def results(self, request):
        """Get backtest results"""
        
        backtest_id = request.query_params.get('id')
        
        if not backtest_id:
            # Return latest backtests
            backtests = BacktestRun.objects.all()[:10]
            serializer = self.get_serializer(backtests, many=True)
            return Response(serializer.data)
        
        try:
            backtest = BacktestRun.objects.get(id=backtest_id)
            serializer = self.get_serializer(backtest)
            return Response(serializer.data)
        
        except BacktestRun.DoesNotExist:
            return Response({
                'error': 'Backtest not found'
            }, status=status.HTTP_404_NOT_FOUND)


class HealthViewSet(viewsets.ViewSet):
    """
    Health check and data validation endpoints
    GET /api/health/status/ - Overall system health
    GET /api/health/data-validation/ - Data quality status
    POST /api/health/validate/ - Run validation
    """
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """Get overall system health"""
        
        # Check database connections
        try:
            # Check if models accessible
            signal_count = AgentSignal.objects.count()
            decision_count = CoordinatorDecision.objects.count()
            
            return Response({
                'status': 'healthy',
                'timestamp': timezone.now().isoformat(),
                'statistics': {
                    'total_signals': signal_count,
                    'total_decisions': decision_count
                }
            })
        
        except Exception as e:
            return Response({
                'status': 'unhealthy',
                'error': str(e)
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    @action(detail=False, methods=['get'], url_path='data-validation')
    def data_validation(self, request):
        """Get data validation status"""
        
        # Get recent validation reports
        reports = ValidationReport.objects.all()[:10]
        
        # Get recent quality metrics
        metrics = DataQualityMetric.objects.all()[:20]
        
        report_data = ValidationReportSerializer(reports, many=True).data
        metric_data = DataQualityMetricSerializer(metrics, many=True).data
        
        # Calculate overall status
        recent_reports = reports[:5]
        all_valid = all([r.is_valid for r in recent_reports]) if recent_reports else True
        
        return Response({
            'status': 'valid' if all_valid else 'issues_detected',
            'recent_reports': report_data,
            'recent_metrics': metric_data
        })
    
    @action(detail=False, methods=['post'])
    def validate(self, request):
        """Run data validation"""
        
        validation_type = request.data.get('type', 'timeseries')
        symbol = request.data.get('symbol', 'EURUSD')
        
        try:
            if validation_type == 'timeseries':
                # Validate time series data
                start_time = (datetime.now() - timedelta(days=30)).isoformat()
                end_time = datetime.now().isoformat()
                
                validator = TimeSeriesValidator(symbol, start_time, end_time)
                result = validator.validate_all()
                
                return Response({
                    'status': 'completed',
                    'is_valid': result.is_valid,
                    'issues': result.issues,
                    'metrics': result.metrics
                })
            
            elif validation_type == 'macro':
                # Validate macro data
                start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
                end_date = datetime.now().strftime('%Y-%m-%d')
                
                validator = MacroDataValidator(start_date, end_date)
                result = validator.validate_and_clean()
                
                return Response({
                    'status': 'completed',
                    'is_valid': result.is_valid,
                    'issues': result.issues,
                    'metrics': result.metrics
                })
            
            elif validation_type == 'news':
                # Process news data
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                end_date = datetime.now().strftime('%Y-%m-%d')
                
                processor = NewsPreprocessor(start_date, end_date)
                result = processor.process()
                
                return Response({
                    'status': 'completed',
                    'result': result
                })
            
            else:
                return Response({
                    'error': f'Unknown validation type: {validation_type}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FeatureViewSet(viewsets.ViewSet):
    """
    Feature engineering endpoints
    POST /api/features/calculate/ - Calculate features
    GET /api/features/status/ - Get feature status
    """
    
    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """Calculate features for a symbol"""
        
        feature_type = request.data.get('type', 'technical')
        symbol = request.data.get('symbol', 'EURUSD')
        
        try:
            if feature_type == 'technical':
                start_time = (datetime.now() - timedelta(days=30)).isoformat()
                end_time = datetime.now().isoformat()
                
                calculator = TechnicalFeaturesCalculator(symbol)
                df = calculator.calculate_all(start_time, end_time)
                
                return Response({
                    'status': 'success',
                    'features_calculated': len(df),
                    'feature_type': 'technical'
                })
            
            elif feature_type == 'macro':
                start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
                end_date = datetime.now().strftime('%Y-%m-%d')
                
                calculator = MacroFeaturesCalculator(symbol)
                df = calculator.calculate_all(start_date, end_date)
                
                return Response({
                    'status': 'success',
                    'features_calculated': len(df),
                    'feature_type': 'macro'
                })
            
            elif feature_type == 'sentiment':
                start_time = (datetime.now() - timedelta(days=7)).isoformat()
                end_time = datetime.now().isoformat()
                
                calculator = SentimentFeaturesCalculator()
                result = calculator.calculate_all(start_time, end_time)
                
                return Response({
                    'status': 'success',
                    'result': result,
                    'feature_type': 'sentiment'
                })
            
            else:
                return Response({
                    'error': f'Unknown feature type: {feature_type}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
