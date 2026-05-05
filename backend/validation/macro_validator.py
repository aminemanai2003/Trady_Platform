"""
PHASE 1: Macro Data Validation Service
Handles missing values, forward-fill, normalization
"""
import pandas as pd
import numpy as np
from typing import Dict, List
from dataclasses import dataclass

from core.database import DatabaseManager
from validation.models import ValidationReport, DataQualityMetric


@dataclass
class MacroValidationResult:
    """Macro validation results"""
    is_valid: bool
    cleaned_data: pd.DataFrame
    issues: List[str]
    metrics: Dict


class MacroDataValidator:
    """Validates and cleans macro economic data"""
    
    ALLOWED_MISSING_RATIO = 0.20  # Max 20% missing allowed
    
    def __init__(self, start_date: str, end_date: str):
        self.start_date = start_date
        self.end_date = end_date
    
    def validate_and_clean(self) -> MacroValidationResult:
        """Validate macro data and apply cleaning strategies"""
        
        # Fetch data
        df = self._fetch_macro_data()
        
        issues = []
        metrics = {}
        
        # 1. Analyze missing values
        missing_analysis = self._analyze_missing_values(df)
        metrics['missing_ratio'] = missing_analysis['overall_ratio']
        
        if missing_analysis['overall_ratio'] > self.ALLOWED_MISSING_RATIO:
            issues.append(f"Missing data ratio {missing_analysis['overall_ratio']:.2%} exceeds threshold")
        
        # 2. Forward-fill with care
        df_cleaned = self._forward_fill_carefully(df, missing_analysis)
        
        # 3. Normalize release frequencies
        df_normalized = self._normalize_frequencies(df_cleaned)
        
        # 4. Detect outliers
        outlier_result = self._detect_outliers(df_normalized)
        if outlier_result['count'] > 0:
            issues.append(f"Found {outlier_result['count']} outliers")
            metrics['outlier_count'] = outlier_result['count']
        
        # 5. Calculate completeness score
        completeness = 1.0 - missing_analysis['overall_ratio']
        metrics['completeness_score'] = completeness
        metrics['total_records'] = len(df)
        
        is_valid = len(issues) == 0 and completeness >= (1 - self.ALLOWED_MISSING_RATIO)
        
        # Save report
        self._save_report(is_valid, issues, metrics, len(df))
        
        return MacroValidationResult(
            is_valid=is_valid,
            cleaned_data=df_normalized,
            issues=issues,
            metrics=metrics
        )
    
    def _fetch_macro_data(self) -> pd.DataFrame:
        """Fetch macro data from PostgreSQL"""
        query = """
            SELECT 
                date,
                series_id,
                value,
                release_name
            FROM macro_data
            WHERE date >= %s AND date <= %s
            ORDER BY date, series_id
        """
        
        with DatabaseManager.get_postgres_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(self.start_date, self.end_date))
        
        # Pivot to wide format
        df_pivot = df.pivot(index='date', columns='series_id', values='value')
        df_pivot.index = pd.to_datetime(df_pivot.index)
        
        return df_pivot
    
    def _analyze_missing_values(self, df: pd.DataFrame) -> Dict:
        """Analyze missing value patterns"""
        total_cells = df.size
        missing_cells = df.isna().sum().sum()
        overall_ratio = missing_cells / total_cells if total_cells > 0 else 0
        
        # Per-column analysis
        column_missing = {}
        for col in df.columns:
            missing_count = df[col].isna().sum()
            missing_ratio = missing_count / len(df)
            column_missing[col] = {
                'count': int(missing_count),
                'ratio': float(missing_ratio)
            }
        
        return {
            'overall_ratio': overall_ratio,
            'total_missing': int(missing_cells),
            'by_column': column_missing
        }
    
    def _forward_fill_carefully(self, df: pd.DataFrame, 
                                 missing_analysis: Dict, 
                                 max_fill_periods: int = 5) -> pd.DataFrame:
        """
        Forward-fill with limits to avoid stale data
        Only fill small gaps, not long missing stretches
        """
        df_filled = df.copy()
        
        for col in df_filled.columns:
            # Only forward-fill up to max_fill_periods
            df_filled[col] = df_filled[col].fillna(method='ffill', limit=max_fill_periods)
        
        return df_filled
    
    def _normalize_frequencies(self, df: pd.DataFrame, 
                               target_freq: str = 'D') -> pd.DataFrame:
        """
        Normalize different release frequencies to common frequency
        Daily by default
        """
        # Resample to target frequency
        df_resampled = df.resample(target_freq).last()
        
        # Forward-fill for weekends/holidays (limited)
        df_resampled = df_resampled.fillna(method='ffill', limit=7)
        
        return df_resampled
    
    def _detect_outliers(self, df: pd.DataFrame, 
                        z_threshold: float = 4.0) -> Dict:
        """Detect outliers using z-score method"""
        outliers = []
        
        for col in df.select_dtypes(include=[np.number]).columns:
            # Calculate z-scores
            mean = df[col].mean()
            std = df[col].std()
            
            if std > 0:
                z_scores = np.abs((df[col] - mean) / std)
                outlier_mask = z_scores > z_threshold
                
                outlier_indices = df[outlier_mask].index
                for idx in outlier_indices:
                    outliers.append({
                        'date': idx.isoformat(),
                        'series': col,
                        'value': float(df.loc[idx, col]),
                        'z_score': float(z_scores.loc[idx])
                    })
        
        return {
            'count': len(outliers),
            'outliers': outliers[:100]
        }
    
    def _save_report(self, is_valid: bool, issues: List[str], 
                    metrics: Dict, records_checked: int):
        """Save validation report"""
        ValidationReport.objects.create(
            report_type=ValidationReport.ReportType.MACRO,
            is_valid=is_valid,
            issues_found=len(issues),
            details={
                'issues': issues,
                'metrics': metrics
            },
            records_checked=records_checked,
            missing_count=int(metrics.get('total_records', 0) * metrics.get('missing_ratio', 0))
        )
        
        DataQualityMetric.objects.create(
            source="macro_data",
            metric_name="completeness_score",
            metric_value=metrics.get('completeness_score', 0),
            threshold=0.80,
            is_passing=metrics.get('completeness_score', 0) >= 0.80
        )
