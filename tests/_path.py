"""Lets the test scripts import the project modules when run as `python tests/xxx.py`."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
