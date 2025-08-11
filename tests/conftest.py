"""
Pytest configuration for cuti tests.
"""

import sys
from pathlib import Path

# Add src to Python path for tests
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))
