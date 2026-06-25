"""Internal relay hub for capacity requests and allocation simulation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from uuid import uuid4


REQUEST_STATUSES = {"active", "paused", "done"}


@dataclass(frozen=True)
class RelayRequest:
    request_id: str
    source: str
    title: str
    requested_tokens: int
    priority: int
    deadline: str
    min_tokens: int
    status: str = "active"
    created_at: str = ""
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "RelayRequest":
        request = cls(
            request_id=str(data["request_id"]),
            source=str(data["source"]),
            title=str(data["title"]),
            requested_tokens=int(data["requested_tokens"]),
            priority=int(data.get("priority", 50)),
            deadline=str(data["deadline"]),
            min_tokens=int(data.get("min_tokens", data["requested_tokens"])),
            status=str(data.get("status", "active")),
            created_at=str(data.get("created_at", utc_now_iso())),
            tags=[str(tag) for tag in data.get("tags", [])],
        )
        request.validate()
        return request

    def to_dict(self) -> dict:
        return asdict(self)

    def validate(self) -> None:
        if not self.request_id:
            raise ValueError("request_id is required")
        if not self.source:
            raise ValueError("source is required")
        if not self.title:
            raise ValueError("title is required")
        if self.requested_tokens <= 0:
            raise ValueError("requested_tokens must be positive")
        if self.min_tokens <= 0:
            raise ValueError("min_tokens must be positive")
        if self.min_tokens > self.requested_tokens:
            raise ValueError("min_tokens cannot exceed requested_tokens")
        if not 0 <= self.priority <= 100:
            raise ValueError("priority must be between 0 and 100")
        if self.status not in REQUEST_STATUSES:
            allowed = ", ".join(sorted(REQUEST_STATUSES))
            raise ValueError(f"status must be one of: {allowed}")
        parse_date(self.deadline)
        parse_timestamp(self.created_at)


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


def load_relay_requests(path: str | Path) -> list[RelayRequest]:
    request_path = Path(path)
    if not request_path.exists():
        return []
    raw = json.loads(request_path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "requests" in raw:
        raw_requests = raw["requests"]
    elif isinstance(raw, list):
        raw_requests = raw
    else:
        raise ValueError("relay requests must be a list or {'requests': [...]}")
    return [RelayRequest.from_dict(item) for item in raw_requests]


def save_relay_requests(path: str | Path, requests: list[RelayRequest]) -> None:
    request_path = Path(path)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [request.to_dict() for request in requests]
    request_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def default_relay_requests(reference_date: date | None = None) -> list[RelayRequest]:
    reference = reference_date or datetime.now(timezone.utc).date()
    created_at = datetime.combine(reference, datetime.min.time(), tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    return [
        RelayRequest(
            request_id="rq-research-001",
            source="research-agent",
            title="Research backlog summarization",
            requested_tokens=80_000,
            min_tokens=30_000,
            priority=92,
            deadline=(reference + timedelta(days=2)).isoformat(),
            created_at=created_at,
            tags=["research", "summary"],
        ),
        RelayRequest(
            request_id="rq-code-002",
            source="engineering",
            title="Batch code review and refactor notes",
            requested_tokens=120_000,
            min_tokens=50_000,
            priority=84,
            deadline=(reference + timedelta(days=4)).isoformat(),
            created_at=created_at,
            tags=["code", "review"],
        ),
        RelayRequest(
            request_id="rq-docs-003",
            source="docs-agent",
            title="Internal documentation sweep",
            requested_tokens=60_000,
            min_tokens=25_000,
            priority=70,
            deadline=(reference + timedelta(days=5)).isoformat(),
            created_at=created_at,
            tags=["docs", "writing"],
        ),
        RelayRequest(
            request_id="rq-eval-004",
            source="eval-agent",
            title="Prompt library regression eval",
            requested_tokens=95_000,
            min_tokens=40_000,
            priority=66,
            deadline=(reference + timedelta(days=6)).isoformat(),
            created_at=created_at,
            tags=["eval", "quality"],
        ),
    ]


def seed_relay_requests(*, data_dir: str | Path, overwrite: bool = False) -> dict:
    data_path = Path(data_dir)
    request_path = data_path / "relay_requests.json"
    if request_path.exists() and not overwrite:
        requests = load_relay_requests(request_path)
        return {"created": False, "requests": len(requests), "relay_requests": str(request_path)}

    requests = default_relay_requests()
    save_relay_requests(request_path, requests)
    return {"created": True, "requests": len(requests), "relay_requests": str(request_path)}


def add_relay_request(
    *,
    data_dir: str | Path,
    source: str,
    title: str,
    requested_tokens: int,
    priority: int,
    deadline: str,
    min_tokens: int | None = None,
    tags: list[str] | None = None,
) -> RelayRequest:
    data_path = Path(data_dir)
    request_path = data_path / "relay_requests.json"
    requests = load_relay_requests(request_path)
    request = RelayRequest(
        request_id=f"rq-{uuid4().hex[:10]}",
        source=source,
        title=title,
        requested_tokens=requested_tokens,
        priority=priority,
        deadline=deadline,
        min_tokens=min_tokens or requested_tokens,
        created_at=utc_now_iso(),
        tags=tags or [],
    )
    requests.append(request)
    save_relay_requests(request_path, requests)
    return request


def rank_requests(requests: list[RelayRequest], reference_date: date | str | None = None) -> list[RelayRequest]:
    reference = parse_date(reference_date) if reference_date is not None else datetime.now(timezone.utc).date()

    def sort_key(request: RelayRequest) -> tuple:
        days_until_deadline = (parse_date(request.deadline) - reference).days
        return (-request.priority, max(days_until_deadline, -999), request.requested_tokens)

    return sorted((request for request in requests if request.status == "active"), key=sort_key)


def allocate_capacity(
    *,
    available_tokens: int,
    requests: list[RelayRequest],
    reference_date: date | str | None = None,
) -> dict:
    available = max(0, int(available_tokens))
    remaining = available
    selected = []
    skipped = []

    for request in rank_requests(requests, reference_date):
        if remaining >= request.requested_tokens:
            allocated = request.requested_tokens
            outcome = "full"
        elif remaining >= request.min_tokens:
            allocated = remaining
            outcome = "partial"
        else:
            skipped.append({**request.to_dict(), "reason": "below_minimum_tokens"})
            continue

        selected.append(
            {
                **request.to_dict(),
                "allocated_tokens": allocated,
                "unfilled_tokens": request.requested_tokens - allocated,
                "outcome": outcome,
            }
        )
        remaining -= allocated
        if remaining <= 0:
            break

    active_requests = [request for request in requests if request.status == "active"]
    selected_ids = {item["request_id"] for item in selected}
    skipped_ids = {item["request_id"] for item in skipped}
    for request in active_requests:
        if request.request_id not in selected_ids and request.request_id not in skipped_ids:
            skipped.append({**request.to_dict(), "reason": "no_capacity_remaining"})

    requested_tokens = sum(request.requested_tokens for request in active_requests)
    allocated_tokens = sum(item["allocated_tokens"] for item in selected)
    coverage_percent = (allocated_tokens / requested_tokens * 100) if requested_tokens else 100.0
    pressure_index = (requested_tokens / available) if available else float(requested_tokens > 0)

    return {
        "available_tokens": available,
        "requested_tokens": requested_tokens,
        "allocated_tokens": allocated_tokens,
        "remaining_tokens": max(0, remaining),
        "coverage_percent": round(coverage_percent, 2),
        "pressure_index": round(pressure_index, 4),
        "selected_requests": selected,
        "skipped_requests": skipped,
    }


def build_relay_report(
    *,
    data_dir: str | Path,
    available_tokens: int,
    reference_date: date | str | None = None,
) -> dict:
    request_path = Path(data_dir) / "relay_requests.json"
    if not request_path.exists():
        seed_relay_requests(data_dir=data_dir)
    requests = load_relay_requests(request_path)
    allocation = allocate_capacity(
        available_tokens=available_tokens,
        requests=requests,
        reference_date=reference_date,
    )
    return {
        "request_count": len(requests),
        "active_request_count": sum(1 for request in requests if request.status == "active"),
        "relay_requests": str(request_path),
        "allocation": allocation,
    }

