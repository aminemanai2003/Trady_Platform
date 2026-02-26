"""
run_full_pipeline.py
Complete Data Preparation Pipeline for Forex Alpha
Executes all steps: EDA → Clean → Engineer → Validate
"""

import sys
from pathlib import Path
from datetime import datetime
import time

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from loguru import logger

# Configure logger
from config import OUTPUT_DIR
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>")
logger.add(OUTPUT_DIR / "full_pipeline.log", rotation="10 MB")

# Import all pipeline scripts
from scripts import (
    explore_data,
    clean_data,
    engineer_features,
    validate_data
)


def print_banner(text):
    """Print a nice banner"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def run_step(step_name, step_function):
    """Run a pipeline step with timing"""
    print_banner(f"STEP: {step_name}")
    start_time = time.time()
    
    try:
        logger.info(f"Starting {step_name}...")
        step_function()
        elapsed = time.time() - start_time
        logger.info(f"✓ {step_name} completed in {elapsed:.1f}s")
        return True, elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"✗ {step_name} failed after {elapsed:.1f}s: {e}")
        return False, elapsed


def main():
    """Execute full data preparation pipeline"""
    
    # Pipeline header
    print("\n" + "=" * 70)
    print("  FOREX ALPHA - COMPLETE DATA PREPARATION PIPELINE")
    print("=" * 70)
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")
    
    print("This pipeline will execute:")
    print("  1. Exploratory Data Analysis (EDA)")
    print("  2. Data Cleaning")
    print("  3. Feature Engineering")
    print("  4. Data Validation")
    print("\n" + "=" * 70 + "\n")
    
    input("Press Enter to start the pipeline...")
    
    # Track pipeline execution
    pipeline_start = time.time()
    steps_results = {}
    
    # Step 1: Exploratory Data Analysis
    success, elapsed = run_step("1. EXPLORATORY DATA ANALYSIS", explore_data.main)
    steps_results['EDA'] = {'success': success, 'time': elapsed}
    
    if not success:
        logger.error("Pipeline stopped due to EDA failure")
        return
    
    # Step 2: Data Cleaning
    success, elapsed = run_step("2. DATA CLEANING", clean_data.main)
    steps_results['Cleaning'] = {'success': success, 'time': elapsed}
    
    if not success:
        logger.error("Pipeline stopped due to cleaning failure")
        return
    
    # Step 3: Feature Engineering
    success, elapsed = run_step("3. FEATURE ENGINEERING", engineer_features.main)
    steps_results['Feature Engineering'] = {'success': success, 'time': elapsed}
    
    if not success:
        logger.error("Pipeline stopped due to feature engineering failure")
        return
    
    # Step 4: Data Validation
    success, elapsed = run_step("4. DATA VALIDATION", validate_data.main)
    steps_results['Validation'] = {'success': success, 'time': elapsed}
    
    # Pipeline summary
    total_time = time.time() - pipeline_start
    
    print_banner("PIPELINE EXECUTION SUMMARY")
    
    print("Step Results:")
    print("-" * 70)
    for step_name, result in steps_results.items():
        status = "✓ SUCCESS" if result['success'] else "✗ FAILED"
        print(f"  {step_name:25s} {status:12s} ({result['time']:.1f}s)")
    
    print("-" * 70)
    print(f"  Total Pipeline Time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
    print("=" * 70 + "\n")
    
    # Check if all steps passed
    all_passed = all(r['success'] for r in steps_results.values())
    
    if all_passed:
        print("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
        print("\nNext Steps:")
        print("  1. Review the output/ folder for reports and visualizations")
        print("  2. Check processed_data/ folder for cleaned and engineered data")
        print("  3. Proceed to model development (Phase 3: Modeling)")
    else:
        print("⚠ PIPELINE COMPLETED WITH ERRORS")
        print("\nPlease review the logs and fix any issues before proceeding.")
    
    print("\n" + "=" * 70 + "\n")
    
    logger.info(f"Pipeline finished. Total time: {total_time:.1f}s")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Pipeline interrupted by user")
        logger.warning("Pipeline interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Pipeline failed with error: {e}")
        logger.error(f"Pipeline failed: {e}")
        raise
