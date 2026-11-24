from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping


@dataclass(frozen=True)
class AuditEntry:
    actor: str
    action: str
    object_id: str
    occurred_at: datetime


def make_entry(actor: str, action: str, object_id: str) -> AuditEntry:
    if not actor.strip() or not action.strip() or not object_id.strip():
        raise ValueError("audit fields must not be empty")
    return AuditEntry(actor, action, object_id, datetime.now(timezone.utc))


def safe_attributes(values: Mapping[str, object]) -> dict[str, str]:
    hidden = {"password", "token", "secret", "authorization"}
    return {
        key: "[redacted]" if key.lower() in hidden else str(value)
        for key, value in values.items()
    }


def group_actions(entries: list[AuditEntry]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for entry in entries:
        totals[entry.action] = totals.get(entry.action, 0) + 1
    return totals
