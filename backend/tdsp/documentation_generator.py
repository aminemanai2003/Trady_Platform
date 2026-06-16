"""
PHASE 7: TDSP Documentation Generator
Automatically generates Team Data Science Process documentation
Exports as JSON or PDF-ready format
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json

from django.db.models import Avg, Count, Q

from validation.models import ValidationReport, DataQualityMetric
from features.models import TechnicalFeatures, MacroFeatures, SentimentFeatures
from agents.models import AgentSignal, CoordinatorDecision, AgentPerformance
from backtesting.models import BacktestRun


class TDSPDocumentationGenerator:
    """
    Generate comprehensive TDSP documentation
    Covers: Data validation, feature importance, agent performance, model drift
    """
    
    def __init__(self, symbol: str = 'EURUSD', lookback_days: int = 30):
        self.symbol = symbol
        self.lookback_days = lookback_days
        self.start_date = datetime.now() - timedelta(days=lookback_days)
    
    def generate_full_report(self) -> Dict:
        """Generate complete TDSP documentation"""
        
        report = {
            'metadata': self._generate_metadata(),
            'data_validation_summary': self._generate_data_validation_summary(),
            'feature_importance_analysis': self._generate_feature_importance_analysis(),
            'agent_performance_comparison': self._generate_agent_performance_comparison(),
            'model_drift_monitoring': self._generate_model_drift_monitoring(),
            'recommendations': self._generate_recommendations()
        }
        
        return report
    
    def _generate_metadata(self) -> Dict:
        """Generate report metadata"""
        
        return {
            'report_generated': datetime.now().isoformat(),
            'symbol': self.symbol,
            'analysis_period': {
                'start': self.start_date.isoformat(),
                'end': datetime.now().isoformat(),
                'days': self.lookback_days
            },
            'system_version': '1.0',
            'methodology': 'Team Data Science Process (TDSP)'
        }
    
    def _generate_data_validation_summary(self) -> Dict:
        """
        Summarize data validation results
        Reports: data quality scores, issues found, trends
        """
        
        # Get recent validation reports
        reports = ValidationReport.objects.filter(
            timestamp__gte=self.start_date
        ).order_by('-timestamp')
        
        summary = {
            'total_validations': reports.count(),
            'by_type': {},
            'quality_trends': [],
            'critical_issues': []
        }
        
        # Group by type
        for report_type in ['timeseries', 'macro', 'news']:
            type_reports = reports.filter(report_type=report_type)
            
            if type_reports.exists():
                valid_count = type_reports.filter(is_valid=True).count()
                total = type_reports.count()
                
                summary['by_type'][report_type] = {
                    'total_validations': total,
                    'valid': valid_count,
                    'invalid': total - valid_count,
                    'validity_rate': (valid_count / total * 100) if total > 0 else 0,
                    'avg_issues': type_reports.aggregate(Avg('issues_found'))['issues_found__avg'] or 0
                }
        
        # Quality trends
        quality_metrics = DataQualityMetric.objects.filter(
            timestamp__gte=self.start_date
        ).order_by('timestamp')
        
        for metric in quality_metrics[:20]:  # Last 20 metrics
            summary['quality_trends'].append({
                'timestamp': metric.timestamp.isoformat(),
                'source': metric.source,
                'metric': metric.metric_name,
                'value': metric.metric_value,
                'passing': metric.is_passing
            })
        
        # Critical issues
        critical_reports = reports.filter(
            is_valid=False,
            issues_found__gte=5
        )[:10]
        
        for report in critical_reports:
            summary['critical_issues'].append({
                'type': report.report_type,
                'timestamp': report.timestamp.isoformat(),
                'issues_count': report.issues_found,
                'details': report.details
            })
        
        return summary
    
    def _generate_feature_importance_analysis(self) -> Dict:
        """
        Analyze feature importance and usage
        Which features are most predictive
        """
        
        analysis = {
            'technical_features': {},
            'macro_features': {},
            'sentiment_features': {},
            'feature_correlations': []
        }
        
        # Technical features statistics
        tech_features = TechnicalFeatures.objects.filter(
            symbol=self.symbol,
            timestamp__gte=self.start_date
        )
        
        if tech_features.exists():
            analysis['technical_features'] = {
                'count': tech_features.count(),
                'key_indicators': {
                    'rsi_14': {
                        'avg': tech_features.aggregate(Avg('rsi_14'))['rsi_14__avg'],
                        'usage_rate': tech_features.filter(rsi_14__isnull=False).count() / tech_features.count()
                    },
                    'macd': {
                        'avg': tech_features.aggregate(Avg('macd'))['macd__avg'],
                        'usage_rate': tech_features.filter(macd__isnull=False).count() / tech_features.count()
                    },
                    'bb_position': {
                        'avg': tech_features.aggregate(Avg('bb_position'))['bb_position__avg'],
                        'usage_rate': tech_features.filter(bb_position__isnull=False).count() / tech_features.count()
                    }
                }
            }
        
        # Macro features statistics
        macro_features = MacroFeatures.objects.filter(
            currency_pair=self.symbol,
            date__gte=self.start_date.date()
        )
        
        if macro_features.exists():
            analysis['macro_features'] = {
                'count': macro_features.count(),
                'key_indicators': {
                    'interest_rate_diff': {
                        'avg': macro_features.aggregate(Avg('interest_rate_diff'))['interest_rate_diff__avg']
                    },
                    'risk_sentiment': {
                        'avg': macro_features.aggregate(Avg('risk_sentiment'))['risk_sentiment__avg']
                    }
                }
            }
        
        # Sentiment features statistics
        sentiment_features = SentimentFeatures.objects.filter(
            timestamp__gte=self.start_date
        )
        
        if sentiment_features.exists():
            analysis['sentiment_features'] = {
                'count': sentiment_features.count(),
                'avg_sentiment': sentiment_features.aggregate(Avg('sentiment_score'))['sentiment_score__avg'],
                'avg_confidence': sentiment_features.aggregate(Avg('confidence'))['confidence__avg'],
                'news_volume': sentiment_features.count()
            }
        
        return analysis
    
    def _generate_agent_performance_comparison(self) -> Dict:
        """
        Compare performance of different agents
        Shows which agent is most accurate
        """
        
        comparison = {
            'agents': {},
            'overall_metrics': {},
            'performance_trends': []
        }
        
        # Get signals for each agent
        for agent_type in ['technical', 'macro', 'sentiment']:
            signals = AgentSignal.objects.filter(
                agent_type=agent_type,
                symbol=self.symbol,
                timestamp__gte=self.start_date
            )
            
            if signals.exists():
                comparison['agents'][agent_type] = {
                    'total_signals': signals.count(),
                    'buy_signals': signals.filter(signal='BUY').count(),
                    'sell_signals': signals.filter(signal='SELL').count(),
                    'neutral_signals': signals.filter(signal='NEUTRAL').count(),
                    'avg_confidence': signals.aggregate(Avg('confidence'))['confidence__avg'],
                    'avg_latency_ms': signals.aggregate(Avg('latency_ms'))['latency_ms__avg']
                }
        
        # Get performance records
        performances = AgentPerformance.objects.filter(
            symbol=self.symbol,
            date__gte=self.start_date.date()
        )
        
        for perf in performances:
            comparison['performance_trends'].append({
                'date': perf.date.isoformat(),
                'agent': perf.agent_type,
                'accuracy': perf.accuracy,
                'sharpe_ratio': perf.sharpe_ratio,
                'current_weight': perf.current_weight
            })
        
        # Overall coordinator performance
        decisions = CoordinatorDecision.objects.filter(
            symbol=self.symbol,
            timestamp__gte=self.start_date
        )
        
        if decisions.exists():
            comparison['overall_metrics'] = {
                'total_decisions': decisions.count(),
                'avg_confidence': decisions.aggregate(Avg('confidence'))['confidence__avg'],
                'risk_distribution': {
                    'low': decisions.filter(risk_level='LOW').count(),
                    'medium': decisions.filter(risk_level='MEDIUM').count(),
                    'high': decisions.filter(risk_level='HIGH').count()
                }
            }
        
        return comparison
    
    def _generate_model_drift_monitoring(self) -> Dict:
        """
        Monitor model drift and performance degradation
        Track changes in agent behavior over time
        """
        
        drift_analysis = {
            'signal_distribution_changes': {},
            'confidence_trends': [],
            'accuracy_degradation': {},
            'alerts': []
        }
        
        # Analyze signal distribution over time
        # Split period into 2 halves and compare
        mid_date = self.start_date + timedelta(days=self.lookback_days // 2)
        
        for agent_type in ['technical', 'macro', 'sentiment']:
            first_half = AgentSignal.objects.filter(
                agent_type=agent_type,
                symbol=self.symbol,
                timestamp__gte=self.start_date,
                timestamp__lt=mid_date
            )
            
            second_half = AgentSignal.objects.filter(
                agent_type=agent_type,
                symbol=self.symbol,
                timestamp__gte=mid_date
            )
            
            if first_half.exists() and second_half.exists():
                first_buy_rate = first_half.filter(signal='BUY').count() / first_half.count()
                second_buy_rate = second_half.filter(signal='BUY').count() / second_half.count()
                
                drift = abs(first_buy_rate - second_buy_rate)
                
                drift_analysis['signal_distribution_changes'][agent_type] = {
                    'first_period_buy_rate': first_buy_rate,
                    'second_period_buy_rate': second_buy_rate,
                    'drift': drift,
                    'significant': drift > 0.2  # More than 20% change
                }
                
                # Generate alert if drift is significant
                if drift > 0.2:
                    drift_analysis['alerts'].append({
                        'type': 'signal_distribution_drift',
                        'agent': agent_type,
                        'severity': 'medium',
                        'message': f'{agent_type} agent showing significant signal distribution change ({drift*100:.1f}%)'
                    })
        
        # Confidence trends
        signals = AgentSignal.objects.filter(
            symbol=self.symbol,
            timestamp__gte=self.start_date
        ).order_by('timestamp')
        
        # Sample every 5th signal to avoid too much data
        for signal in signals[::5]:
            drift_analysis['confidence_trends'].append({
                'timestamp': signal.timestamp.isoformat(),
                'agent': signal.agent_type,
                'confidence': signal.confidence
            })
        
        return drift_analysis
    
    def _generate_recommendations(self) -> List[Dict]:
        """
        Generate actionable recommendations based on analysis
        """
        
        recommendations = []
        
        # Check data quality
        recent_validations = ValidationReport.objects.filter(
            timestamp__gte=self.start_date
        )
        
        invalid_rate = recent_validations.filter(is_valid=False).count() / max(recent_validations.count(), 1)
        
        if invalid_rate > 0.2:
            recommendations.append({
                'priority': 'high',
                'category': 'data_quality',
                'title': 'High data quality issues detected',
                'description': f'{invalid_rate*100:.1f}% of validations failed',
                'action': 'Review data pipeline and fix data quality issues'
            })
        
        # Check agent performance
        for agent_type in ['technical', 'macro', 'sentiment']:
            perf = AgentPerformance.objects.filter(
                agent_type=agent_type,
                symbol=self.symbol
            ).order_by('-date').first()
            
            if perf and perf.accuracy < 0.5:
                recommendations.append({
                    'priority': 'medium',
                    'category': 'agent_performance',
                    'title': f'{agent_type.capitalize()} agent underperforming',
                    'description': f'Accuracy: {perf.accuracy*100:.1f}%',
                    'action': f'Review {agent_type} agent configuration and retrain if necessary'
                })
        
        # Check backtest results
        recent_backtest = BacktestRun.objects.filter(
            symbol=self.symbol,
            status=BacktestRun.Status.COMPLETED
        ).order_by('-created_at').first()
        
        if recent_backtest:
            if recent_backtest.sharpe_ratio and recent_backtest.sharpe_ratio < 1.0:
                recommendations.append({
                    'priority': 'medium',
                    'category': 'strategy_performance',
                    'title': 'Low Sharpe ratio detected',
                    'description': f'Sharpe ratio: {recent_backtest.sharpe_ratio:.2f}',
                    'action': 'Consider adjusting agent weights or risk parameters'
                })
        
        # Default recommendation if none
        if not recommendations:
            recommendations.append({
                'priority': 'low',
                'category': 'general',
                'title': 'System performing nominally',
                'description': 'No critical issues detected',
                'action': 'Continue monitoring and maintain regular validation schedule'
            })
        
        return recommendations
    
    def export_json(self, filepath: str = None) -> str:
        """Export report as JSON"""
        
        report = self.generate_full_report()
        
        if filepath:
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            return filepath
        else:
            return json.dumps(report, indent=2, default=str)
    
    def export_markdown(self, filepath: str = None) -> str:
        """Export report as Markdown (PDF-ready)"""
        
        report = self.generate_full_report()
        
        md_content = f"""# TDSP Documentation Report

**Generated:** {report['metadata']['report_generated']}  
**Symbol:** {report['metadata']['symbol']}  
**Period:** {report['metadata']['analysis_period']['days']} days

---

## 1. Data Validation Summary

### Overview
- Total Validations: {report['data_validation_summary']['total_validations']}

### By Type
"""
        
        for dtype, data in report['data_validation_summary']['by_type'].items():
            md_content += f"""
**{dtype.capitalize()}**
- Total: {data['total_validations']}
- Valid: {data['valid']}
- Validity Rate: {data['validity_rate']:.1f}%
"""
        
        md_content += f"""

---

## 2. Feature Importance Analysis

### Technical Features
- Total Features: {report['feature_importance_analysis']['technical_features'].get('count', 0)}

### Macro Features
- Total Features: {report['feature_importance_analysis']['macro_features'].get('count', 0)}

### Sentiment Features
- Total Features: {report['feature_importance_analysis']['sentiment_features'].get('count', 0)}

---

## 3. Agent Performance Comparison

### Overall Metrics
- Total Decisions: {report['agent_performance_comparison']['overall_metrics'].get('total_decisions', 0)}
- Average Confidence: {report['agent_performance_comparison']['overall_metrics'].get('avg_confidence', 0):.3f}

### By Agent
"""
        
        for agent, data in report['agent_performance_comparison']['agents'].items():
            md_content += f"""
**{agent.capitalize()} Agent**
- Total Signals: {data['total_signals']}
- Buy: {data['buy_signals']} | Sell: {data['sell_signals']} | Neutral: {data['neutral_signals']}
- Avg Confidence: {data['avg_confidence']:.3f}
"""
        
        md_content += f"""

---

## 4. Model Drift Monitoring

### Alerts
"""
        
        alerts = report['model_drift_monitoring']['alerts']
        if alerts:
            for alert in alerts:
                md_content += f"- **[{alert['severity'].upper()}]** {alert['message']}\n"
        else:
            md_content += "- No drift alerts\n"
        
        md_content += """

---

## 5. Recommendations

"""
        
        for rec in report['recommendations']:
            md_content += f"""
### {rec['title']} [{rec['priority'].upper()}]
**Category:** {rec['category']}  
**Description:** {rec['description']}  
**Action:** {rec['action']}

"""
        
        if filepath:
            with open(filepath, 'w') as f:
                f.write(md_content)
            return filepath
        else:
            return md_content
