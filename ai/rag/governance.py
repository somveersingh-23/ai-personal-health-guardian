from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class KnowledgeBaseAudit:
    total: int
    clinically_sourced: int
    issues: tuple[str, ...]

    @property
    def production_ready(self) -> bool:
        return self.total > 0 and self.clinically_sourced == self.total and not self.issues


def audit_knowledge_base(path: Path, *, today: date | None = None) -> KnowledgeBaseAudit:
    issues: list[str] = []
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            issues.append(f"line {line_number}: invalid JSON")
    clinically_sourced = 0
    current = today or date.today()
    for record in records:
        chunk = record.get("chunk_id", "unknown")
        source_url = record.get("source_url")
        tags = set(record.get("safety_tags", []))
        if source_url and record.get("review_status") == "clinically_approved":
            clinically_sourced += 1
        else:
            issues.append(f"{chunk}: clinical source/sign-off missing")
        expires = record.get("expires_on")
        if expires and date.fromisoformat(expires) < current:
            issues.append(f"{chunk}: review expired")
        if "non_diagnostic" not in tags:
            issues.append(f"{chunk}: non_diagnostic safety tag missing")
    return KnowledgeBaseAudit(len(records), clinically_sourced, tuple(issues))
