from __future__ import annotations

import sys
from pathlib import Path

SRC_PYTHON_DIR = Path(__file__).resolve().parents[1]
if str(SRC_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_PYTHON_DIR))
