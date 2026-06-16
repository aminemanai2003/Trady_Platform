"""
PHASE 1: Time-Series Validation Service
Detects missing timestamps, duplicates, gaps, OHLC consistency
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from dataclasses import dataclass

from core.database import TimeSeriesQuery
from validation.models import ValidationReport, DataQualityMetric


@dataclass
class ValidationResult:
    """Container for validation results"""
    is_valid: bool
    issues: List[str]
    metrics: Dict[str, float]
    details: Dict


class TimeSeriesValidator:
    """Validates OHLCV data integrity"""
    
    def __init__(self, symbol: str, start_time: str, end_time: str):
        self.symbol = symbol
        self.start_time = start_time
        self.end_time = end_time
    
    def validate_all(self) -> ValidationResult:
        """Run all validation checks"""
        
        # Fetch data
        df = self._fetch_data()
        
        issues = []
        metrics = {}
        details = {}
        
        # 1. Check for missing timestamps
        missing_result = self._check_missing_timestamps(df)
        if missing_result['count'] > 0:
            issues.append(f"Missing {missing_result['count']} timestamps")
            details['missing_timestamps'] = missing_result['timestamps']
        metrics['missing_count'] = missing_result['count']
        
        # 2. Check for duplicates
        duplicate_result = self._check_duplicates(df)
        if duplicate_result['count'] > 0:
            issues.append(f"Found {duplicate_result['count']} duplicate candles")
            details['duplicate_timestamps'] = duplicate_result['timestamps']
        metrics['duplicate_count'] = duplicate_result['count']
        
        # 3. Validate timezone consistency
        tz_result = self._check_timezone_consistency(df)
        if not tz_result['is_consistent']:
            issues.append("Timezone inconsistency detected")
        details['timezone_info'] = tz_result
        
        # 4. Check for abnormal gaps
        gap_result = self._check_abnormal_gaps(df)
        if gap_result['count'] > 0:
            issues.append(f"Found {gap_result['count']} abnormal gaps")
            details['abnormal_gaps'] = gap_result['gaps']
        metrics['gap_count'] = gap_result['count']
        
        # 5. Validate OHLC logical consistency
        ohlc_result = self._validate_ohlc_logic(df)
        if ohlc_result['invalid_count'] > 0:
            issues.append(f"{ohlc_result['invalid_count']} OHLC inconsistencies")
            details['ohlc_issues'] = ohlc_result['invalid_indices']
        metrics['ohlc_invalid_count'] = ohlc_result['invalid_count']
        
        # Calculate quality score
        total_records = len(df)
        total_issues = sum([missing_result['count'], duplicate_result['count'], 
                           gap_result['count'], ohlc_result['invalid_count']])
        
        quality_score = 1.0 - (total_issues / max(total_records, 1))
        metrics['quality_score'] = quality_score
        metrics['total_records'] = total_records
        
        is_valid = len(issues) == 0
        
        # Store in database
        self._save_report(is_valid, issues, metrics, details, total_records)
        
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            metrics=metrics,
            details=details
        )
    
    def _fetch_data(self) -> pd.DataFrame:
        """Fetch OHLCV data from InfluxDB"""
        result = TimeSeriesQuery.query_ohlcv(
            self.symbol, 
            self.start_time, 
            self.end_time
        )
        
        # Convert to pandas
        records = []
        for table in result:
            for record in table.records:
                records.append({
                    'time': record.get_time(),
                    'open': record.values.get('open'),
                    'high': record.values.get('high'),
                    'low': record.values.get('low'),
                    'close': record.values.get('close'),
                    'volume': record.values.get('volume')
                })
        
        df = pd.DataFrame(records)
        df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values('time').reset_index(drop=True)
        
        return df
    
    def _check_missing_timestamps(self, df: pd.DataFrame, 
                                   expected_freq: str = '5min') -> Dict:
        """Check for missing timestamps in expected frequency"""
        if len(df) == 0:
            return {'count': 0, 'timestamps': []}
        
        # Create expected time range
        expected_range = pd.date_range(
            start=df['time'].min(),
            end=df['time'].max(),
            freq=expected_freq
        )
        
        # Find missing timestamps
        actual_times = set(df['time'])
        expected_times = set(expected_range)
        missing_times = expected_times - actual_times
        
        return {
            'count': len(missing_times),
            'timestamps': [t.isoformat() for t in sorted(missing_times)[:100]]  # Limit to 100
        }
    
    def _check_duplicates(self, df: pd.DataFrame) -> Dict:
        """Check for duplicate timestamps"""
        duplicates = df[df.duplicated(subset=['time'], keep=False)]
        
        return {
            'count': len(duplicates),
            'timestamps': duplicates['time'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist()[:100]
        }
    
    def _check_timezone_consistency(self, df: pd.DataFrame) -> Dict:
        """Validate timezone consistency"""
        if len(df) == 0:
            return {'is_consistent': True, 'timezone': None}
        
        # Check if all timestamps have same timezone
        timezones = df['time'].dt.tz
        unique_tzs = timezones.unique()
        
        return {
            'is_consistent': len(unique_tzs) == 1,
            'timezone': str(unique_tzs[0]) if len(unique_tzs) == 1 else None,
            'unique_timezones': [str(tz) for tz in unique_tzs]
        }
    
    def _check_abnormal_gaps(self, df: pd.DataFrame, 
                            max_gap_minutes: int = 30) -> Dict:
        """Identify abnormal gaps between consecutive timestamps"""
        if len(df) < 2:
            return {'count': 0, 'gaps': []}
        
        df = df.sort_values('time')
        time_diffs = df['time'].diff()
        
        # Find gaps larger than expected
        max_gap = timedelta(minutes=max_gap_minutes)
        abnormal_mask = time_diffs > max_gap
        
        abnormal_gaps = []
        for idx in df[abnormal_mask].index:
            abnormal_gaps.append({
                'start': df.loc[idx-1, 'time'].isoformat(),
                'end': df.loc[idx, 'time'].isoformat(),
                'gap_minutes': time_diffs.loc[idx].total_seconds() / 60
            })
        
        return {
            'count': len(abnormal_gaps),
            'gaps': abnormal_gaps[:100]  # Limit to 100
        }
    
    def _validate_ohlc_logic(self, df: pd.DataFrame) -> Dict:
        """Validate OHLC logical consistency: high >= open/close >= low"""
        if len(df) == 0:
            return {'invalid_count': 0, 'invalid_indices': []}
        
        # Check conditions
        invalid_mask = (
            (df['high'] < df['open']) |
            (df['high'] < df['close']) |
            (df['low'] > df['open']) |
            (df['low'] > df['close']) |
            (df['high'] < df['low'])
        )
        
        invalid_df = df[invalid_mask]
        
        invalid_details = []
        for idx, row in invalid_df.iterrows():
            invalid_details.append({
                'time': row['time'].isoformat(),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close'])
            })
        
        return {
            'invalid_count': len(invalid_df),
            'invalid_indices': invalid_details[:100]
        }
    
    def _save_report(self, is_valid: bool, issues: List[str], 
                    metrics: Dict, details: Dict, records_checked: int):
        """Save validation report to database"""
        ValidationReport.objects.create(
            report_type=ValidationReport.ReportType.TIMESERIES,
            symbol=self.symbol,
            is_valid=is_valid,
            issues_found=len(issues),
            details={
                'issues': issues,
                'metrics': metrics,
                'details': details
            },
            records_checked=records_checked,
            missing_count=int(metrics.get('missing_count', 0)),
            duplicate_count=int(metrics.get('duplicate_count', 0)),
            anomaly_count=int(metrics.get('gap_count', 0))
        )
        
        # Save quality metrics
        DataQualityMetric.objects.create(
            source=f"timeseries_{self.symbol}",
            metric_name="quality_score",
            metric_value=metrics.get('quality_score', 0),
            threshold=0.95,
            is_passing=metrics.get('quality_score', 0) >= 0.95
        )
