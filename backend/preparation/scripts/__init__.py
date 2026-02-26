"""
Scripts Package
Contains all data preparation pipeline scripts
"""

from pathlib import Path
import sys

# Add scripts to path
scripts_dir = Path(__file__).parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

# These will be imported by run_full_pipeline
import explore_data
import clean_data
import engineer_features
import validate_data

__all__ = [
    'explore_data',
    'clean_data',
    'engineer_features',
    'validate_data'
]
