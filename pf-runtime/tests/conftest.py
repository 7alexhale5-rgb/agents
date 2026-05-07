"""Shared pytest fixtures for the pf-runtime test suite."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure pf_runtime imports work whether tests are run from the project root
# or from within the tests/ directory.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
