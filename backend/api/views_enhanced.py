"""
Enhanced API Views for V2 + Decision Pipeline
Integrates LLM Judge + Risk Management + XAI
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import datetime
from typing import Optional

from decision_layer.pipeline import TradingDecisionPipeline
from monitoring.safety_monitor import SafetyMonitor
from data_layer.news_loader import NewsLoader


class EnhancedTradingSignalViewSet(viewsets.ViewSet):
    """
    Enhanced API endpoints with full decision pipeline:
    Coordinator → Actuarial → Judge → Risk → XAI
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize with default capital (can be configured per request)
        self.pipeline = TradingDecisionPipeline(initial_capital=10000.0)
        self.safety_monitor = SafetyMonitor()
        self.news_loader = NewsLoader()
    
    @action(detail=False, methods=['post'])
    def generate_with_pipeline(self, request):
        """
        Generate trading signal with full validation pipeline.
        
        POST /api/v2/signals/generate_with_pipeline/
        Body: {
            "pair": "EURUSD",
            "capital": 10000.0  (optional),
            "current_equity": 10200.0  (optional),
            "peak_equity": 10500.0  (optional),
            "current_positions": 2  (optional)
        }
        
        Returns:
        - Final decision (APPROVED / REJECTED)
        - Position sizing (if approved)
        - Complete XAI explanation
        - Rejection reason (if rejected)
        """
        # Parse request
        pair = request.data.get('pair', 'EURUSD')
        capital = float(request.data.get('capital', 10000.0))
        current_equity = float(request.data.get('current_equity', capital))
        peak_equity = float(request.data.get('peak_equity', capital))
        current_positions = int(request.data.get('current_positions', 0))
        entry_price = request.data.get('entry_price')  # Optional
        
        # Parse currency pair
        if len(pair) == 6:
            base = pair[:3]
            quote = pair[3:6]
        else:
            base = 'EUR'
            quote = 'USD'
        
        symbol = pair
        
        # Update pipeline equity tracking
        self.pipeline.capital = capital
        self.pipeline.update_equity(current_equity, current_positions)
        if peak_equity > self.pipeline.peak_equity:
            self.pipeline.peak_equity = peak_equity
        
        # Safety check (pre-pipeline)
        safety_check = self.safety_monitor.should_allow_signal(symbol)
        
        if not safety_check['allowed']:
            return Response({
                'success': False,
                'decision': 'BLOCKED',
                'reason': safety_check['reason'],
                'safety_checks': safety_check
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Execute decision pipeline
        try:
            result = self.pipeline.execute(
                symbol=symbol,
                base_currency=base,
                quote_currency=quote,
                entry_price=entry_price,
                market_context={
                    'latest_news_count': self._get_recent_news_count(symbol),
                    'request_time': datetime.now().isoformat()
                }
            )
            
            # Check if error
            if result.get('status') == 'error':
                return Response({
                    'success': False,
                    'error': result.get('error'),
                    'timestamp': result.get('timestamp')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Format response based on status
            if result['status'] == 'success':
                # APPROVED trade
                return Response({
                    'success': True,
                    'decision': result['decision'],
                    'signal': {
                        'direction': result['signal_name'],
                        'signal_value': result['signal'],
                        'confidence': result['confidence'],
                        'symbol': result['symbol']
                    },
                    'execution_plan': {
                        'entry_price': result['entry_price'],
                        'position_size': result['position_size'],
                        'stop_loss': result['stop_loss'],
                        'take_profit': result['take_profit'],
                        'stop_loss_pips': result['stop_loss_pips'],
                        'take_profit_pips': result['take_profit_pips'],
                        'risk_pct': result['risk_pct']
                    },
                    'expected_outcome': {
                        'expected_value_pips': result['expected_value_pips'],
                        'probability_win': result['probability_win']
                    },
                    'xai': result['xai'],
                    'timestamp': result['timestamp']
                })
            
            else:
                # REJECTED trade
                return Response({
                    'success': True,  # Request succeeded, but trade was rejected
                    'decision': result['decision'],
                    'signal': {
                        'direction': result['signal_name'],
                        'signal_value': result['signal'],
                        'confidence': result['confidence'],
                        'symbol': result['symbol']
                    },
                    'rejection': {
                        'stage': result.get('rejection_stage'),
                        'reason': result.get('rejection_reason')
                    },
                    'xai': result['xai'],
                    'timestamp': result['timestamp']
                })
        
        except Exception as e:
            import traceback
            return Response({
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc(),
                'timestamp': datetime.now().isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def risk_status(self, request):
        """
        Get current risk status.
        
        GET /api/v2/signals/risk_status/
        Params:
            - capital (optional)
            - current_equity (optional)
            - peak_equity (optional)
            - current_positions (optional)
        
        Returns available risk capacity
        """
        capital = float(request.query_params.get('capital', self.pipeline.capital))
        current_equity = float(request.query_params.get('current_equity', self.pipeline.current_equity))
        peak_equity = float(request.query_params.get('peak_equity', self.pipeline.peak_equity))
        current_positions = int(request.query_params.get('current_positions', self.pipeline.current_positions))
        
        # Update pipeline
        self.pipeline.capital = capital
        self.pipeline.update_equity(current_equity, current_positions)
        if peak_equity > self.pipeline.peak_equity:
            self.pipeline.peak_equity = peak_equity
        
        risk_status = self.pipeline.get_risk_status()
        emergency_stop = self.pipeline.check_emergency_stop()
        
        return Response({
            'risk_status': risk_status,
            'emergency_stop': emergency_stop,
            'account': {
                'capital': self.pipeline.capital,
                'current_equity': self.pipeline.current_equity,
                'peak_equity': self.pipeline.peak_equity,
                'current_positions': self.pipeline.current_positions
            },
            'timestamp': datetime.now().isoformat()
        })
    
    @action(detail=False, methods=['post'])
    def update_equity(self, request):
        """
        Update equity tracking.
        
        POST /api/v2/signals/update_equity/
        Body: {
            "current_equity": 10200.0,
            "current_positions": 2
        }
        """
        current_equity = float(request.data.get('current_equity'))
        current_positions = int(request.data.get('current_positions', 0))
        
        self.pipeline.update_equity(current_equity, current_positions)
        
        return Response({
            'success': True,
            'updated': {
                'current_equity': self.pipeline.current_equity,
                'peak_equity': self.pipeline.peak_equity,
                'current_positions': self.pipeline.current_positions
            },
            'timestamp': datetime.now().isoformat()
        })
    
    def _get_recent_news_count(self, symbol: str) -> int:
        """Get count of recent news articles"""
        try:
            # Extract currencies from symbol
            if len(symbol) == 6:
                currencies = [symbol[:3], symbol[3:6]]
            else:
                currencies = ['EUR', 'USD']
            
            # Get recent news
            news = self.news_loader.load_recent_news(currencies=currencies, hours=24)
            return len(news) if news is not None else 0
        except:
            return 0
