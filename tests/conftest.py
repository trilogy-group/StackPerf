"""Pytest configuration for tests."""

import sys
from pathlib import Path

# Add src to Python path for imports
SRC_DIR = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))
