"""Path configuration for Member 3 pytest tests.

Adds both the repository root and the ``backend/`` directory to
``sys.path`` so that test modules in this package can import from:

- ``ml.*``   (repository root — safety engine)
- ``ai.*``   (repository root — assistant provider / prompts)
- ``app.*``  (backend/ — schemas, services, API)

Pytest discovers and executes this file before importing any test module
in the same directory or its sub-directories, so no ``sys.path`` changes
are needed inside individual test files.

Ownership: Member 3 only.  No shared or other-member files are affected.
"""

import sys
from pathlib import Path

# This file lives at backend/tests/member3/conftest.py.
# Walk up three levels to reach the repository root.
_THIS_DIR = Path(__file__).parent.resolve()           # backend/tests/member3/
_BACKEND_TESTS = _THIS_DIR.parent                     # backend/tests/
_BACKEND = _BACKEND_TESTS.parent                      # backend/
_REPO_ROOT = _BACKEND.parent                          # repo root

for _path in (_REPO_ROOT, _BACKEND):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.insert(0, _path_str)
