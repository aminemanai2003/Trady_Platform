"""
Data Validator Module
Validate data quality and integrity using various checks
"""

import pandas as pd
import numpy as np
from loguru import logger
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import sys

# Configure logger
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")


class DataValidator:
    """Validate data quality and business rules"""
    
    def __init__(self, validation_config: Optional[Dict] = None):
        """
        Initialize DataValidator
        
        Args:
            validation_config: Configuration dict with thresholds
        """
        self.config = validation_config or {
            'min_data_points': 1000,
            'max_missing_ratio': 0.05,
            'outlier_std_threshold': 3,
            'min_date': '2020-01-01',
            'max_date': '2026-12-31'
        }
        self.validation_results = {}
    
    def validate_schema(self, df: pd.DataFrame, required_columns: List[str]) -> Dict:
        """
        Validate DataFrame schema
        
        Args:
            df: DataFrame to validate
            required_columns: List of required column names
            
        Returns:
            Validation result dictionary
        """
        logger.info("Validating schema...")
        
        missing_columns = set(required_columns) - set(df.columns)
        extra_columns = set(df.columns) - set(required_columns)
        
        result = {
            'test': 'schema_validation',
            'passed': len(missing_columns) == 0,
            'missing_columns': list(missing_columns),
            'extra_columns': list(extra_columns),
            'actual_columns': list(df.columns)
        }
        
        if result['passed']:
            logger.info("✓ Schema validation passed")
        else:
            logger.error(f"✗ Schema validation failed: missing {missing_columns}")
        
        return result
    
    def validate_data_types(self, df: pd.DataFrame, expected_types: Dict[str, str]) -> Dict:
        """
        Validate column data types
        
        Args:
            df: DataFrame to validate
            expected_types: Dict mapping column name to expected type
            
        Returns:
            Validation result dictionary
        """
        logger.info("Validating data types...")
        
        mismatches = []
        
        for col, expected_type in expected_types.items():
            if col not in df.columns:
                continue
            
            actual_type = str(df[col].dtype)
            
            # Check if types match (allow some flexibility)
            type_match = False
            if expected_type == 'numeric' and df[col].dtype in [np.float64, np.int64, np.float32, np.int32]:
                type_match = True
            elif expected_type == 'datetime' and pd.api.types.is_datetime64_any_dtype(df[col]):
                type_match = True
            elif expected_type == 'string' and df[col].dtype == object:
                type_match = True
            elif expected_type in actual_type:
                type_match = True
            
            if not type_match:
                mismatches.append({
                    'column': col,
                    'expected': expected_type,
                    'actual': actual_type
                })
        
        result = {
            'test': 'data_type_validation',
            'passed': len(mismatches) == 0,
            'mismatches': mismatches
        }
        
        if result['passed']:
            logger.info("✓ Data type validation passed")
        else:
            logger.warning(f"⚠ Data type mismatches: {len(mismatches)}")
        
        return result
    
    def validate_completeness(self, df: pd.DataFrame) -> Dict:
        """
        Check data completeness (missing values)
        
        Args:
            df: DataFrame to validate
            
        Returns:
            Validation result dictionary
        """
        logger.info("Validating data completeness...")
        
        total_rows = len(df)
        max_missing = int(total_rows * self.config['max_missing_ratio'])
        
        completeness_report = []
        all_passed = True
        
        for col in df.columns:
            missing_count = df[col].isna().sum()
            missing_ratio = missing_count / total_rows
            passed = missing_count <= max_missing
            
            if not passed:
                all_passed = False
            
            completeness_report.append({
                'column': col,
                'missing_count': int(missing_count),
                'missing_ratio': float(missing_ratio),
                'passed': passed
            })
        
        result = {
            'test': 'completeness_validation',
            'passed': all_passed,
            'max_missing_ratio': self.config['max_missing_ratio'],
            'details': completeness_report
        }
        
        if result['passed']:
            logger.info("✓ Completeness validation passed")
        else:
            logger.warning("⚠ Some columns exceed missing value threshold")
        
        return result
    
    def validate_uniqueness(self, df: pd.DataFrame, unique_columns: List[str]) -> Dict:
        """
        Validate uniqueness constraints
        
        Args:
            df: DataFrame to validate
            unique_columns: List of columns that should have unique combinations
            
        Returns:
            Validation result dictionary
        """
        logger.info(f"Validating uniqueness for: {unique_columns}")
        
        total_rows = len(df)
        unique_rows = len(df[unique_columns].drop_duplicates())
        duplicates = total_rows - unique_rows
        
        result = {
            'test': 'uniqueness_validation',
            'passed': duplicates == 0,
            'total_rows': total_rows,
            'unique_rows': unique_rows,
            'duplicate_rows': duplicates,
            'columns_checked': unique_columns
        }
        
        if result['passed']:
            logger.info("✓ Uniqueness validation passed")
        else:
            logger.warning(f"⚠ Found {duplicates} duplicate rows")
        
        return result
    
    def validate_range(self, df: pd.DataFrame, column: str, min_val: Optional[float] = None, 
                      max_val: Optional[float] = None) -> Dict:
        """
        Validate numeric column is within expected range
        
        Args:
            df: DataFrame to validate
            column: Column name
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            
        Returns:
            Validation result dictionary
        """
        logger.info(f"Validating range for column: {column}")
        
        if column not in df.columns:
            return {'test': 'range_validation', 'passed': False, 'error': 'Column not found'}
        
        violations = []
        
        if min_val is not None:
            below_min = (df[column] < min_val).sum()
            if below_min > 0:
                violations.append(f"{below_min} values below {min_val}")
        
        if max_val is not None:
            above_max = (df[column] > max_val).sum()
            if above_max > 0:
                violations.append(f"{above_max} values above {max_val}")
        
        result = {
            'test': 'range_validation',
            'column': column,
            'passed': len(violations) == 0,
            'min_expected': min_val,
            'max_expected': max_val,
            'min_actual': float(df[column].min()),
            'max_actual': float(df[column].max()),
            'violations': violations
        }
        
        if result['passed']:
            logger.info(f"✓ Range validation passed for {column}")
        else:
            logger.warning(f"⚠ Range violations: {', '.join(violations)}")
        
        return result
    
    def validate_date_range(self, df: pd.DataFrame, date_column: str) -> Dict:
        """
        Validate dates are within expected range
        
        Args:
            df: DataFrame to validate
            date_column: Name of date column
            
        Returns:
            Validation result dictionary
        """
        logger.info(f"Validating date range for: {date_column}")
        
        if date_column not in df.columns:
            return {'test': 'date_range_validation', 'passed': False, 'error': 'Column not found'}
        
        # Convert to datetime if needed
        dates = pd.to_datetime(df[date_column])
        
        min_date = pd.to_datetime(self.config['min_date'])
        max_date = pd.to_datetime(self.config['max_date'])
        
        before_min = (dates < min_date).sum()
        after_max = (dates > max_date).sum()
        
        result = {
            'test': 'date_range_validation',
            'column': date_column,
            'passed': before_min == 0 and after_max == 0,
            'min_expected': str(min_date.date()),
            'max_expected': str(max_date.date()),
            'min_actual': str(dates.min().date()),
            'max_actual': str(dates.max().date()),
            'before_min': int(before_min),
            'after_max': int(after_max)
        }
        
        if result['passed']:
            logger.info(f"✓ Date range validation passed")
        else:
            logger.warning(f"⚠ Date range issues: {before_min} before min, {after_max} after max")
        
        return result
    
    def validate_no_future_dates(self, df: pd.DataFrame, date_column: str) -> Dict:
        """
        Ensure no dates are in the future
        
        Args:
            df: DataFrame to validate
            date_column: Name of date column
            
        Returns:
            Validation result dictionary
        """
        logger.info(f"Checking for future dates in: {date_column}")
        
        if date_column not in df.columns:
            return {'test': 'no_future_dates', 'passed': False, 'error': 'Column not found'}
        
        dates = pd.to_datetime(df[date_column])
        now = pd.Timestamp.now()
        
        future_dates = (dates > now).sum()
        
        result = {
            'test': 'no_future_dates',
            'column': date_column,
            'passed': future_dates == 0,
            'future_count': int(future_dates),
            'current_time': str(now)
        }
        
        if result['passed']:
            logger.info("✓ No future dates found")
        else:
            logger.warning(f"⚠ Found {future_dates} future dates")
        
        return result
    
    def validate_ohlc_consistency(self, df: pd.DataFrame) -> Dict:
        """
        Validate OHLC data consistency (high >= low, etc.)
        
        Args:
            df: DataFrame with OHLC columns
            
        Returns:
            Validation result dictionary
        """
        logger.info("Validating OHLC consistency...")
        
        required_cols = ['open', 'high', 'low', 'close']
        if not all(col in df.columns for col in required_cols):
            return {'test': 'ohlc_consistency', 'passed': False, 'error': 'Missing OHLC columns'}
        
        violations = []
        
        # High >= Low
        high_low_violations = (df['high'] < df['low']).sum()
        if high_low_violations > 0:
            violations.append(f"{high_low_violations} where high < low")
        
        # High >= Open
        high_open_violations = (df['high'] < df['open']).sum()
        if high_open_violations > 0:
            violations.append(f"{high_open_violations} where high < open")
        
        # High >= Close
        high_close_violations = (df['high'] < df['close']).sum()
        if high_close_violations > 0:
            violations.append(f"{high_close_violations} where high < close")
        
        # Low <= Open
        low_open_violations = (df['low'] > df['open']).sum()
        if low_open_violations > 0:
            violations.append(f"{low_open_violations} where low > open")
        
        # Low <= Close
        low_close_violations = (df['low'] > df['close']).sum()
        if low_close_violations > 0:
            violations.append(f"{low_close_violations} where low > close")
        
        result = {
            'test': 'ohlc_consistency',
            'passed': len(violations) == 0,
            'total_rows': len(df),
            'violations': violations
        }
        
        if result['passed']:
            logger.info("✓ OHLC consistency validation passed")
        else:
            logger.error(f"✗ OHLC violations: {', '.join(violations)}")
        
        return result
    
    def validate_minimum_records(self, df: pd.DataFrame) -> Dict:
        """
        Validate minimum number of records
        
        Args:
            df: DataFrame to validate
            
        Returns:
            Validation result dictionary
        """
        logger.info("Validating minimum record count...")
        
        actual_count = len(df)
        min_required = self.config['min_data_points']
        
        result = {
            'test': 'minimum_records',
            'passed': actual_count >= min_required,
            'actual_count': actual_count,
            'min_required': min_required
        }
        
        if result['passed']:
            logger.info(f"✓ Sufficient records: {actual_count:,} >= {min_required:,}")
        else:
            logger.error(f"✗ Insufficient records: {actual_count:,} < {min_required:,}")
        
        return result
    
    def validate_time_continuity(self, df: pd.DataFrame, time_column: str, expected_freq: str = 'D') -> Dict:
        """
        Validate time series continuity (no large gaps)
        
        Args:
            df: DataFrame to validate
            time_column: Name of time column
            expected_freq: Expected frequency ('D', 'H', etc.)
            
        Returns:
            Validation result dictionary
        """
        logger.info(f"Validating time continuity (expected freq: {expected_freq})...")
        
        if time_column not in df.columns:
            return {'test': 'time_continuity', 'passed': False, 'error': 'Column not found'}
        
        df_sorted = df.sort_values(time_column).reset_index(drop=True)
        dates = pd.to_datetime(df_sorted[time_column])
        
        # Calculate time differences
        time_diffs = dates.diff()
        
        # Define acceptable gap based on frequency
        freq_thresholds = {
            'D': timedelta(days=7),    # Allow up to 7 days gap (weekends)
            'H': timedelta(hours=24),   # Allow up to 24 hours gap
            '4H': timedelta(hours=48),  # Allow up to 48 hours gap
        }
        
        max_gap = freq_thresholds.get(expected_freq, timedelta(days=30))
        
        large_gaps = (time_diffs > max_gap).sum()
        
        result = {
            'test': 'time_continuity',
            'column': time_column,
            'passed': large_gaps == 0,
            'expected_freq': expected_freq,
            'max_acceptable_gap': str(max_gap),
            'large_gaps_found': int(large_gaps)
        }
        
        if result['passed']:
            logger.info("✓ Time continuity validation passed")
        else:
            logger.warning(f"⚠ Found {large_gaps} large time gaps")
        
        return result
    
    def run_all_validations(self, df: pd.DataFrame, data_type: str = 'ohlc') -> Dict:
        """
        Run all applicable validations
        
        Args:
            df: DataFrame to validate
            data_type: Type of data ('ohlc', 'economic', 'news')
            
        Returns:
            Complete validation report
        """
        logger.info("=" * 60)
        logger.info(f"RUNNING ALL VALIDATIONS - {data_type.upper()}")
        logger.info("=" * 60)
        
        results = {
            'data_type': data_type,
            'timestamp': datetime.now().isoformat(),
            'total_records': len(df),
            'validations': []
        }
        
        # Common validations
        results['validations'].append(self.validate_minimum_records(df))
        results['validations'].append(self.validate_completeness(df))
        
        # Type-specific validations
        if data_type == 'ohlc':
            required_cols = ['time', 'open', 'high', 'low', 'close', 'symbol']
            results['validations'].append(self.validate_schema(df, required_cols))
            results['validations'].append(self.validate_ohlc_consistency(df))
            
            if 'time' in df.columns:
                results['validations'].append(self.validate_no_future_dates(df, 'time'))
        
        elif data_type == 'economic':
            required_cols = ['date', 'series_id', 'value']
            results['validations'].append(self.validate_schema(df, required_cols))
            
            if 'date' in df.columns:
                results['validations'].append(self.validate_date_range(df, 'date'))
                results['validations'].append(self.validate_no_future_dates(df, 'date'))
            
            if 'date' in df.columns and 'series_id' in df.columns:
                results['validations'].append(self.validate_uniqueness(df, ['date', 'series_id']))
        
        elif data_type == 'news':
            required_cols = ['url', 'title', 'published_at']
            results['validations'].append(self.validate_schema(df, required_cols))
            
            if 'url' in df.columns:
                results['validations'].append(self.validate_uniqueness(df, ['url']))
        
        # Summary
        total_tests = len(results['validations'])
        passed_tests = sum(1 for v in results['validations'] if v.get('passed', False))
        failed_tests = total_tests - passed_tests
        
        results['summary'] = {
            'total_tests': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'pass_rate': f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%",
            'overall_passed': failed_tests == 0
        }
        
        logger.info("=" * 60)
        logger.info(f"VALIDATION SUMMARY: {passed_tests}/{total_tests} tests passed")
        logger.info("=" * 60)
        
        return results
    
    def print_validation_report(self, results: Dict):
        """Print formatted validation report"""
        print("\n" + "=" * 70)
        print(f"  VALIDATION REPORT - {results['data_type'].upper()}")
        print("=" * 70)
        print(f"  Timestamp: {results['timestamp']}")
        print(f"  Total Records: {results['total_records']:,}")
        print("=" * 70)
        
        for validation in results['validations']:
            status = "✓ PASS" if validation['passed'] else "✗ FAIL"
            test_name = validation['test'].replace('_', ' ').title()
            print(f"\n  [{status}] {test_name}")
            
            # Print relevant details
            if not validation['passed']:
                if 'violations' in validation and validation['violations']:
                    for violation in validation['violations']:
                        print(f"          {violation}")
                if 'missing_columns' in validation and validation['missing_columns']:
                    print(f"          Missing: {validation['missing_columns']}")
        
        print("\n" + "=" * 70)
        print(f"  SUMMARY: {results['summary']['passed']}/{results['summary']['total_tests']} tests passed ({results['summary']['pass_rate']})")
        print("=" * 70 + "\n")


if __name__ == '__main__':
    # Test the DataValidator
    
    # Create sample OHLC data
    dates = pd.date_range('2020-01-01', periods=50, freq='D')
    close_prices = 100 + np.cumsum(np.random.randn(50))
    
    data = {
        'time': dates,
        'open': close_prices + np.random.randn(50) * 0.5,
        'high': close_prices + np.abs(np.random.randn(50)),
        'low': close_prices - np.abs(np.random.randn(50)),
        'close': close_prices,
        'symbol': ['EURUSD'] * 50,
        'timeframe': ['1D'] * 50
    }
    
    df_test = pd.DataFrame(data)
    
    print("\n" + "=" * 60)
    print("TESTING DATA VALIDATOR")
    print("=" * 60)
    
    validator = DataValidator()
    results = validator.run_all_validations(df_test, data_type='ohlc')
    validator.print_validation_report(results)
