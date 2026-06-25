"""Usage logging and aggregation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Iterable


SESSION_TYPES = {"chat", "api", "batch"}


@dataclass(frozen=True)
class UsageRecord:
    timestamp: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_estimate: float = 0.0
    session_type: str = "chat"

    @property
    def total_tokens(self) -> int:
        return self.tokens_in + self.tokens_out

    @classmethod
    def from_dict(cls, data: dict) -> "UsageRecord":
        record = cls(
            timestamp=str(data["timestamp"]),
            model=str(data["model"]),
            tokens_in=int(data["tokens_in"]),
            tokens_out=int(data["tokens_out"]),
            cost_estimate=float(data.get("cost_estimate", 0.0)),
            session_type=str(data.get("session_type", "chat")),
        )
        record.validate()
        return record

    def to_dict(self) -> dict:
        return asdict(self)

    def validate(self) -> None:
        if not self.model:
            raise ValueError("model is required")
        if self.tokens_in < 0 or self.tokens_out < 0:
            raise ValueError("token counts must be non-negative")
        if self.cost_estimate < 0:
            raise ValueError("cost_estimate must be non-negative")
        if self.session_type not in SESSION_TYPES:
            allowed = ", ".join(sorted(SESSION_TYPES))
            raise ValueError(f"session_type must be one of: {allowed}")
        parse_timestamp(self.timestamp)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(value).date()


def load_usage_log(path: str | Path) -> list[UsageRecord]:
    log_path = Path(path)
    if not log_path.exists():
        return []
    raw = json.loads(log_path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "records" in raw:
        raw_records = raw["records"]
    elif isinstance(raw, dict):
        raw_records = [raw]
    elif isinstance(raw, list):
        raw_records = raw
    else:
        raise ValueError("usage log must be a list, an object, or {'records': [...]}")
    return [UsageRecord.from_dict(item) for item in raw_records]


def save_usage_log(path: str | Path, records: Iterable[UsageRecord]) -> None:
    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [record.to_dict() for record in records]
    log_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def append_usage(
    path: str | Path,
    *,
    model: str,
    tokens_in: int,
    tokens_out: int,
    cost_estimate: float = 0.0,
    session_type: str = "chat",
    timestamp: str | None = None,
) -> UsageRecord:
    records = load_usage_log(path)
    record = UsageRecord(
        timestamp=timestamp or utc_now_iso(),
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_estimate=cost_estimate,
        session_type=session_type,
    )
    record.validate()
    records.append(record)
    save_usage_log(path, records)
    return record


def aggregate_daily_tokens(
    records: Iterable[UsageRecord],
    *,
    start_date: date | str | None = None,
    end_date: date | str | None = None,
) -> dict[str, int]:
    start = parse_date(start_date) if start_date is not None else None
    end = parse_date(end_date) if end_date is not None else None
    totals: dict[str, int] = {}
    for record in records:
        record_date = parse_timestamp(record.timestamp).date()
        if start is not None and record_date < start:
            continue
        if end is not None and record_date > end:
            continue
        key = record_date.isoformat()
        totals[key] = totals.get(key, 0) + record.total_tokens
    return dict(sorted(totals.items()))


def dense_daily_history(
    records: Iterable[UsageRecord],
    *,
    start_date: date | str,
    end_date: date | str,
) -> list[dict]:
    start = parse_date(start_date)
    end = parse_date(end_date)
    if end < start:
        return []

    totals = aggregate_daily_tokens(records, start_date=start, end_date=end)
    history: list[dict] = []
    cursor = start
    while cursor <= end:
        key = cursor.isoformat()
        history.append({"date": key, "tokens": totals.get(key, 0)})
        cursor += timedelta(days=1)
    return history


def total_tokens(records: Iterable[UsageRecord]) -> int:
    return sum(record.total_tokens for record in records)


def latest_record_date(records: Iterable[UsageRecord]) -> date | None:
    dates = [parse_timestamp(record.timestamp).date() for record in records]
    return max(dates) if dates else None

