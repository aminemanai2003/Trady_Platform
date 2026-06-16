"""
PHASE 6: Django REST API Serializers
"""
from rest_framework import serializers
from agents.models import AgentSignal, CoordinatorDecision, AgentPerformance
from backtesting.models import BacktestRun, BacktestTrade
from validation.models import ValidationReport, DataQualityMetric


class AgentSignalSerializer(serializers.ModelSerializer):
    """Serializer for agent signals"""
    
    class Meta:
        model = AgentSignal
        fields = '__all__'


class CoordinatorDecisionSerializer(serializers.ModelSerializer):
    """Serializer for coordinator decisions"""
    
    technical_signal = AgentSignalSerializer(read_only=True)
    macro_signal = AgentSignalSerializer(read_only=True)
    sentiment_signal = AgentSignalSerializer(read_only=True)
    
    class Meta:
        model = CoordinatorDecision
        fields = '__all__'


class AgentPerformanceSerializer(serializers.ModelSerializer):
    """Serializer for agent performance metrics"""
    
    class Meta:
        model = AgentPerformance
        fields = '__all__'


class BacktestTradeSerializer(serializers.ModelSerializer):
    """Serializer for backtest trades"""
    
    class Meta:
        model = BacktestTrade
        fields = '__all__'


class BacktestRunSerializer(serializers.ModelSerializer):
    """Serializer for backtest runs"""
    
    trades = BacktestTradeSerializer(many=True, read_only=True)
    
    class Meta:
        model = BacktestRun
        fields = '__all__'


class ValidationReportSerializer(serializers.ModelSerializer):
    """Serializer for validation reports"""
    
    class Meta:
        model = ValidationReport
        fields = '__all__'


class DataQualityMetricSerializer(serializers.ModelSerializer):
    """Serializer for data quality metrics"""
    
    class Meta:
        model = DataQualityMetric
        fields = '__all__'
