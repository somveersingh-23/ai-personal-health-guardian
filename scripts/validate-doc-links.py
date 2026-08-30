"""Fail when repository Markdown points to a missing local file or directory."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
SKIP_PARTS = frozenset({".git", ".gradle", ".venv", "build", "data", "node_modules"})


def _local_target(raw_target: str) -> str | None:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    # An optional Markdown title follows a whitespace-delimited URL.
    target = target.split(maxsplit=1)[0]
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    return unquote(parsed.path)


def validate(root: Path) -> tuple[int, list[str]]:
    checked = 0
    failures: list[str] = []
    for document in sorted(root.rglob("*.md")):
        if SKIP_PARTS.intersection(document.relative_to(root).parts):
            continue
        text = document.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in LINK_PATTERN.finditer(line):
                target = _local_target(match.group(1))
                if target is None:
                    continue
                checked += 1
                candidate = (document.parent / target).resolve()
                try:
                    candidate.relative_to(root.resolve())
                except ValueError:
                    failures.append(
                        f"{document.relative_to(root)}:{line_number}: target escapes repository: {target}"
                    )
                    continue
                if not candidate.exists():
                    failures.append(
                        f"{document.relative_to(root)}:{line_number}: missing target: {target}"
                    )
    return checked, failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()
    checked, failures = validate(args.root.resolve())
    if failures:
        raise SystemExit("Broken documentation links:\n" + "\n".join(failures))
    print(f"Validated {checked} local Markdown link(s).")


if __name__ == "__main__":
    main()
