"""Repository-root conftest.py — path configuration for pytest.

Adds both the repository root and the ``backend/`` directory to
``sys.path`` so that test modules can import from:

- ``ml.*``        (repo root)
- ``ai.*``        (repo root)
- ``app.*``       (backend/)

This file does not modify any existing source files.
"""

import sys
from pathlib import Path

# Repository root (this file's parent).
_REPO_ROOT = Path(__file__).parent.resolve()
# Backend package root.
_BACKEND = _REPO_ROOT / "backend"

for _path in (_REPO_ROOT, _BACKEND):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.insert(0, _path_str)
