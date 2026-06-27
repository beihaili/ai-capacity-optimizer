"""LiteLLM export normalization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from aco.backend.usage_tracker import UsageRecord, load_usage_log, save_usage_log, total_tokens


def load_litellm_spend_logs(path: str | Path) -> list[dict]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "records" in raw:
        raw = raw["records"]
    elif isinstance(raw, dict) and "spend_logs" in raw:
        raw = raw["spend_logs"]
    elif isinstance(raw, dict) and "data" in raw:
        raw = raw["data"]
    if not isinstance(raw, list):
        raise ValueError("LiteLLM spend log export must be a list or contain records, spend_logs, or data")
    return [dict(item) for item in raw]


def load_litellm_budget(path: str | Path | None) -> dict | None:
    if path is None:
        return None
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "budget" in raw:
        raw = raw["budget"]
    if not isinstance(raw, dict):
        raise ValueError("LiteLLM budget export must be an object or contain budget")
    return raw


def litellm_session_type(call_type: object) -> str:
    value = str(call_type or "").lower()
    if "batch" in value:
        return "batch"
    if value in {"chat", "chat_completion"}:
        return "chat"
    return "api"


def normalize_litellm_spend_log(row: dict) -> UsageRecord:
    timestamp = row.get("startTime") or row.get("endTime")
    if timestamp is None:
        raise ValueError("LiteLLM spend log row is missing startTime or endTime")

    prompt_tokens = int(row.get("prompt_tokens", 0))
    completion_tokens = int(row.get("completion_tokens", 0))
    if prompt_tokens == 0 and completion_tokens == 0 and row.get("total_tokens") is not None:
        prompt_tokens = int(row["total_tokens"])

    record = UsageRecord(
        timestamp=str(timestamp),
        model=str(row["model"]),
        tokens_in=prompt_tokens,
        tokens_out=completion_tokens,
        cost_estimate=float(row.get("spend", 0.0)),
        session_type=litellm_session_type(row.get("call_type")),
    )
    record.validate()
    return record


def normalize_litellm_spend_logs(rows: Iterable[dict]) -> list[UsageRecord]:
    return [normalize_litellm_spend_log(row) for row in rows]


def import_litellm_exports(
    *,
    spend_log_path: str | Path,
    output_path: str | Path,
    budget_path: str | Path | None = None,
    append: bool = False,
) -> dict:
    spend_rows = load_litellm_spend_logs(spend_log_path)
    imported_records = normalize_litellm_spend_logs(spend_rows)
    existing_records = load_usage_log(output_path) if append else []
    records = [*existing_records, *imported_records]
    save_usage_log(output_path, records)
    budget = load_litellm_budget(budget_path)

    return {
        "source": "litellm",
        "spend_log": str(spend_log_path),
        "budget": summarize_litellm_budget(budget),
        "output": str(output_path),
        "append": append,
        "imported_records": len(imported_records),
        "total_records": len(records),
        "imported_tokens": total_tokens(imported_records),
        "total_tokens": total_tokens(records),
    }


def summarize_litellm_budget(budget: dict | None) -> dict | None:
    if budget is None:
        return None
    keys = [
        "budget_id",
        "soft_budget",
        "max_budget",
        "budget_duration",
        "budget_reset_at",
        "created_at",
        "allowed_models",
        "model_max_budget",
        "tpm_limit",
        "rpm_limit",
    ]
    return {key: budget[key] for key in keys if key in budget}
