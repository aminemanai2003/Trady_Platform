"""
04_validate_data.py
Data Validation Pipeline for Forex Alpha Data
Validates data quality using comprehensive checks
"""

import pandas as pd
import sys
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config import PROCESSED_DATA_DIR, OUTPUT_DIR, VALIDATION_CONFIG
from utils import DataValidator
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")
logger.add(OUTPUT_DIR / "validation.log", rotation="10 MB")


def validate_economic_data():
    """Validate cleaned economic indicators"""
    logger.info("=" * 70)
    logger.info("VALIDATING ECONOMIC INDICATORS")
    logger.info("=" * 70)
    
    # Load cleaned data
    input_path = PROCESSED_DATA_DIR / 'economic_indicators_clean.parquet'
    
    if not input_path.exists():
        logger.warning("Economic data not found")
        return None
    
    df = pd.read_parquet(input_path)
    logger.info(f"Loaded {len(df):,} records")
    
    # Initialize validator
    validator = DataValidator(VALIDATION_CONFIG)
    
    # Run all validations
    results = validator.run_all_validations(df, data_type='economic')
    
    # Print report
    validator.print_validation_report(results)
    
    return results


def validate_news_data():
    """Validate cleaned news articles"""
    logger.info("=" * 70)
    logger.info("VALIDATING NEWS ARTICLES")
    logger.info("=" * 70)
    
    # Load cleaned data
    input_path = PROCESSED_DATA_DIR / 'news_articles_clean.parquet'
    
    if not input_path.exists():
        logger.warning("News data not found")
        return None
    
    df = pd.read_parquet(input_path)
    logger.info(f"Loaded {len(df):,} articles")
    
    # Initialize validator
    validator = DataValidator(VALIDATION_CONFIG)
    
    # Run all validations
    results = validator.run_all_validations(df, data_type='news')
    
    # Print report
    validator.print_validation_report(results)
    
    return results


def validate_ohlc_data(symbol: str, timeframe: str = '1D'):
    """Validate OHLC price data for a specific symbol"""
    logger.info(f"Validating {symbol} {timeframe}...")
    
    # Load cleaned data
    filename = f'ohlc_{symbol}_{timeframe}_clean.parquet'
    input_path = PROCESSED_DATA_DIR / filename
    
    if not input_path.exists():
        logger.warning(f"  ⚠ File not found: {input_path}")
        return None
    
    df = pd.read_parquet(input_path)
    logger.info(f"  Loaded {len(df):,} candles")
    
    # Initialize validator
    validator = DataValidator(VALIDATION_CONFIG)
    
    # Run all validations
    results = validator.run_all_validations(df, data_type='ohlc')
    
    # Print report
    validator.print_validation_report(results)
    
    return results


def validate_features_data(symbol: str, timeframe: str = '1D'):
    """Validate feature-engineered OHLC data"""
    logger.info(f"Validating features for {symbol} {timeframe}...")
    
    # Load feature-engineered data
    filename = f'ohlc_{symbol}_{timeframe}_features.parquet'
    input_path = PROCESSED_DATA_DIR / filename
    
    if not input_path.exists():
        logger.warning(f"  ⚠ File not found: {input_path}")
        return None
    
    df = pd.read_parquet(input_path)
    logger.info(f"  Loaded {len(df):,} rows with {len(df.columns)} columns")
    
    # Custom validations for features
    validator = DataValidator(VALIDATION_CONFIG)
    
    results = {
        'data_type': f'features_{symbol}_{timeframe}',
        'timestamp': datetime.now().isoformat(),
        'total_records': len(df),
        'total_features': len(df.columns),
        'validations': []
    }
    
    # Check for infinite values
    inf_count = np.isinf(df.select_dtypes(include=[np.number])).sum().sum()
    results['validations'].append({
        'test': 'no_infinite_values',
        'passed': inf_count == 0,
        'infinite_count': int(inf_count)
    })
    
    if inf_count > 0:
        logger.warning(f"  ⚠ Found {inf_count} infinite values")
    else:
        logger.info("  ✓ No infinite values")
    
    # Check for NaN values
    nan_count = df.isna().sum().sum()
    results['validations'].append({
        'test': 'no_nan_values',
        'passed': nan_count == 0,
        'nan_count': int(nan_count)
    })
    
    if nan_count > 0:
        logger.warning(f"  ⚠ Found {nan_count} NaN values")
    else:
        logger.info("  ✓ No NaN values")
    
    # Check minimum records
    results['validations'].append(validator.validate_minimum_records(df))
    
    # Summary
    total_tests = len(results['validations'])
    passed_tests = sum(1 for v in results['validations'] if v.get('passed', False))
    
    results['summary'] = {
        'total_tests': total_tests,
        'passed': passed_tests,
        'failed': total_tests - passed_tests,
        'pass_rate': f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%",
        'overall_passed': total_tests == passed_tests
    }
    
    logger.info(f"  ✓ Validation: {passed_tests}/{total_tests} tests passed")
    
    return results


def create_validation_summary(all_results):
    """Create comprehensive validation summary"""
    logger.info("=" * 70)
    logger.info("CREATING VALIDATION SUMMARY")
    logger.info("=" * 70)
    
    summary_path = OUTPUT_DIR / 'validation_summary.txt'
    
    with open(summary_path, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("FOREX ALPHA - DATA VALIDATION SUMMARY\n")
        f.write("=" * 70 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 70 + "\n\n")
        
        total_datasets = len(all_results)
        passed_datasets = sum(1 for r in all_results.values() if r and r.get('summary', {}).get('overall_passed', False))
        
        f.write(f"OVERALL VALIDATION RESULTS:\n\n")
        f.write(f"  Datasets Validated: {total_datasets}\n")
        f.write(f"  Datasets Passed: {passed_datasets}\n")
        f.write(f"  Datasets Failed: {total_datasets - passed_datasets}\n")
        f.write(f"  Success Rate: {(passed_datasets/total_datasets)*100:.1f}%\n\n")
        
        f.write("=" * 70 + "\n")
        f.write("DETAILS BY DATASET:\n")
        f.write("=" * 70 + "\n\n")
        
        for dataset_name, result in all_results.items():
            if result is None:
                continue
            
            summary = result.get('summary', {})
            f.write(f"\n{dataset_name.upper()}:\n")
            f.write(f"  Records: {result.get('total_records', 'N/A'):,}\n")
            f.write(f"  Tests: {summary.get('passed', 0)}/{summary.get('total_tests', 0)} passed\n")
            f.write(f"  Status: {'✓ PASS' if summary.get('overall_passed', False) else '✗ FAIL'}\n")
            
            # List failed tests
            failed_tests = [v for v in result.get('validations', []) if not v.get('passed', True)]
            if failed_tests:
                f.write(f"  Failed tests:\n")
                for test in failed_tests:
                    f.write(f"    - {test.get('test', 'Unknown')}\n")
        
        f.write("\n" + "=" * 70 + "\n")
        f.write("RECOMMENDATIONS:\n")
        f.write("=" * 70 + "\n\n")
        
        if passed_datasets == total_datasets:
            f.write("✓ All datasets passed validation!\n")
            f.write("✓ Data quality is excellent and ready for modeling.\n\n")
        else:
            f.write("⚠ Some datasets failed validation.\n")
            f.write("⚠ Review failed tests and rerun cleaning if necessary.\n")
            f.write("⚠ Consider additional data quality checks.\n\n")
        
        f.write("NEXT STEPS:\n")
        f.write("1. Review any failed validations\n")
        f.write("2. Proceed to feature selection\n")
        f.write("3. Split data for training/testing\n")
        f.write("4. Begin model development\n\n")
    
    logger.info(f"✓ Saved validation summary: {summary_path}")


def main():
    """Main validation execution"""
    print("\n" + "=" * 70)
    print("  FOREX ALPHA - DATA VALIDATION PIPELINE")
    print("=" * 70)
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")
    
    validation_report = {
        'timestamp': datetime.now().isoformat(),
        'results': {}
    }
    
    try:
        # Validate economic indicators
        eco_results = validate_economic_data()
        if eco_results:
            validation_report['results']['economic_indicators'] = eco_results
        
        # Validate news articles
        news_results = validate_news_data()
        if news_results:
            validation_report['results']['news_articles'] = news_results
        
        # Validate OHLC data for each currency pair
        from config import CURRENCY_PAIRS
        
        logger.info("=" * 70)
        logger.info("VALIDATING OHLC PRICE DATA")
        logger.info("=" * 70)
        
        for symbol in CURRENCY_PAIRS:
            # Validate cleaned data
            ohlc_results = validate_ohlc_data(symbol, '1D')
            if ohlc_results:
                validation_report['results'][f'ohlc_{symbol}_clean'] = ohlc_results
            
            # Validate feature-engineered data
            features_results = validate_features_data(symbol, '1D')
            if features_results:
                validation_report['results'][f'ohlc_{symbol}_features'] = features_results
        
        # Create validation summary
        create_validation_summary(validation_report['results'])
        
        # Save validation report
        report_path = OUTPUT_DIR / 'validation_report.json'
        with open(report_path, 'w') as f:
            json.dump(validation_report, f, indent=2, default=str)
        
        logger.info(f"\n✓ Saved validation report: {report_path}")
        
        # Print final summary
        print("\n" + "=" * 70)
        print("  VALIDATION SUMMARY")
        print("=" * 70)
        
        total_datasets = len(validation_report['results'])
        passed_datasets = sum(1 for r in validation_report['results'].values() 
                            if r and r.get('summary', {}).get('overall_passed', False))
        
        print(f"\nDatasets Validated: {total_datasets}")
        print(f"Datasets Passed: {passed_datasets}")
        print(f"Success Rate: {(passed_datasets/total_datasets)*100:.1f}%")
        
        if passed_datasets == total_datasets:
            print("\n✓ ALL VALIDATIONS PASSED!")
        else:
            print(f"\n⚠ {total_datasets - passed_datasets} dataset(s) failed validation")
        
        print("\n" + "=" * 70)
        
        logger.info("\n✓ DATA VALIDATION COMPLETED")
        
    except Exception as e:
        logger.error(f"✗ Error during validation: {e}")
        raise
    
    print("\n" + "=" * 70)
    print("  VALIDATION COMPLETE - Check output/ folder")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    import numpy as np
    main()
