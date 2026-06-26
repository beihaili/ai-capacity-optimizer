"""Request accounting for the unified API."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from aco.backend.quota_model import load_quota_config, save_quota_config
from aco.backend.usage_tracker import append_usage, load_usage_log, total_tokens, utc_now_iso


@dataclass(frozen=True)
class RequestLogRecord:
    timestamp: str
    request_id: str
    provider_id: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float
    status: str
    live: bool
    latency_ms: int
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def load_request_log(path: str | Path) -> list[RequestLogRecord]:
    log_path = Path(path)
    if not log_path.exists():
        return []
    raw = json.loads(log_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("request log must be a list")
    return [
        RequestLogRecord(
            timestamp=str(item["timestamp"]),
            request_id=str(item["request_id"]),
            provider_id=str(item["provider_id"]),
            provider=str(item["provider"]),
            model=str(item["model"]),
            prompt_tokens=int(item.get("prompt_tokens", 0)),
            completion_tokens=int(item.get("completion_tokens", 0)),
            total_tokens=int(item.get("total_tokens", 0)),
            estimated_cost=float(item.get("estimated_cost", 0.0)),
            status=str(item.get("status", "unknown")),
            live=bool(item.get("live", False)),
            latency_ms=int(item.get("latency_ms", 0)),
            error=str(item.get("error", "")),
        )
        for item in raw
    ]


def save_request_log(path: str | Path, records: list[RequestLogRecord]) -> None:
    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps([record.to_dict() for record in records], indent=2), encoding="utf-8")


def append_request_log(path: str | Path, record: RequestLogRecord) -> RequestLogRecord:
    records = load_request_log(path)
    records.append(record)
    save_request_log(path, records)
    return record


def normalize_usage(usage: dict | None, fallback: dict | None = None) -> dict:
    source = usage or fallback or {}
    prompt_tokens = int(source.get("prompt_tokens", source.get("tokens_in", 0)) or 0)
    completion_tokens = int(source.get("completion_tokens", source.get("tokens_out", 0)) or 0)
    total_tokens = int(source.get("total_tokens", prompt_tokens + completion_tokens) or 0)
    if total_tokens and not prompt_tokens and not completion_tokens:
        prompt_tokens = total_tokens
    elif not total_tokens:
        total_tokens = prompt_tokens + completion_tokens
    return {
        "prompt_tokens": max(0, prompt_tokens),
        "completion_tokens": max(0, completion_tokens),
        "total_tokens": max(0, total_tokens),
    }


def estimate_cost(provider: dict, total_tokens: int) -> float:
    return round((total_tokens / 1000) * float(provider.get("cost_per_1k_tokens", 0.0)), 6)


def record_gateway_attempt(
    *,
    data_dir: str | Path,
    route: dict,
    provider: dict,
    usage: dict | None,
    status: str,
    live: bool,
    latency_ms: int,
    error: str = "",
) -> dict:
    data_path = Path(data_dir)
    usage_data = normalize_usage(usage, route.get("estimated_usage") if status == "success" else None)
    cost = estimate_cost(provider, usage_data["total_tokens"]) if status == "success" else 0.0
    record = RequestLogRecord(
        timestamp=utc_now_iso(),
        request_id=str(route["request_id"]),
        provider_id=str(provider["provider_id"]),
        provider=str(provider["provider"]),
        model=str(provider["model"]),
        prompt_tokens=usage_data["prompt_tokens"],
        completion_tokens=usage_data["completion_tokens"],
        total_tokens=usage_data["total_tokens"],
        estimated_cost=cost,
        status=status,
        live=live,
        latency_ms=max(0, int(latency_ms)),
        error=error,
    )
    append_request_log(data_path / "request_log.json", record)

    if status == "success":
        append_usage(
            data_path / "usage_log.json",
            model=record.model,
            tokens_in=record.prompt_tokens,
            tokens_out=record.completion_tokens,
            cost_estimate=record.estimated_cost,
            session_type="api",
            timestamp=record.timestamp,
        )
        sync_quota_usage(data_path)

    return record.to_dict()


def sync_quota_usage(data_dir: str | Path) -> None:
    data_path = Path(data_dir)
    quota_path = data_path / "quota_config.json"
    if not quota_path.exists():
        return
    quota = load_quota_config(quota_path)
    records = load_usage_log(data_path / "usage_log.json")
    save_quota_config(quota_path, quota.with_current_usage(total_tokens(records)))
