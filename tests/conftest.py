import sys
from pathlib import Path

# Ensure the src/ directory is on the import path for tests.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
