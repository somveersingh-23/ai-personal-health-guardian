"""Repository and privacy-safe data path resolution."""

from __future__ import annotations

import os
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def data_root() -> Path:
    """Return the configured local data root; this directory is Git-ignored."""

    configured = os.getenv("HEALTH_GUARDIAN_DATA_ROOT")
    root = Path(configured).expanduser() if configured else REPOSITORY_ROOT / "data"
    return root.resolve()


def require_within(root: Path, candidate: Path) -> Path:
    """Reject path traversal before a downloader or extractor writes anything."""

    resolved_root = root.resolve()
    resolved_candidate = candidate.resolve()
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"path escapes configured data root: {resolved_candidate}") from exc
    return resolved_candidate
