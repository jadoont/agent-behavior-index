from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class LogRecord:
    level: str
    event: str
    fields: dict[str, str]
    timestamp: datetime


class InventoryLogger:
    def __init__(self, service_name: str):
        if not service_name.strip():
            raise ValueError("service name is required")
        self.service_name = service_name
        self.records: list[LogRecord] = []

    def emit(self, level: str, event: str, fields: dict[str, object]) -> LogRecord:
        normalized = {key: str(value) for key, value in fields.items()}
        record = LogRecord(
            level.upper(),
            f"{self.service_name}.{event}",
            normalized,
            datetime.now(timezone.utc),
        )
        self.records.append(record)
        return record

    def recent(self, limit: int = 20) -> list[LogRecord]:
        if limit < 0:
            raise ValueError("log limit cannot be negative")
        return self.records[-limit:] if limit else []


def render_record(record: LogRecord) -> str:
    values = " ".join(f"{key}={value}" for key, value in sorted(record.fields.items()))
    return f"{record.timestamp.isoformat()} {record.level} {record.event} {values}".rstrip()
