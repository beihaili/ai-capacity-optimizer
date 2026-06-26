"""Mock data generation for local demos."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import random
from pathlib import Path

from aco.backend.accounting import save_request_log
from aco.backend.api_gateway import default_provider_pool, save_provider_pool
from aco.backend.quota_model import QuotaConfig, cycle_dates, default_quota_config, load_quota_config, save_quota_config, today_utc
from aco.backend.relay_hub import default_relay_requests, save_relay_requests
from aco.backend.usage_tracker import UsageRecord, parse_timestamp, save_usage_log


MODEL_UNIT_COSTS = {
    "gpt-4o": 0.000012,
    "gpt-4o-mini": 0.000003,
    "claude-3-5-sonnet": 0.000011,
}


def generate_mock_records(*, start_date: date, days: int = 30, seed: int = 7) -> list[UsageRecord]:
    if days <= 0:
        raise ValueError("days must be positive")

    rng = random.Random(seed)
    records: list[UsageRecord] = []
    models = list(MODEL_UNIT_COSTS)
    session_types = ["chat", "api", "batch"]

    for offset in range(days):
        day = date.fromordinal(start_date.toordinal() + offset)
        trend = offset * 320
        weekly_shape = 4_500 if day.weekday() < 5 else 2_000
        noise = rng.randint(-2_500, 3_500)
        daily_total = max(1_500, 8_500 + trend + weekly_shape + noise)
        sessions = rng.randint(2, 6)
        remaining = daily_total

        for session_idx in range(sessions):
            if session_idx == sessions - 1:
                tokens = remaining
            else:
                tokens = rng.randint(1_000, max(1_000, remaining // 2))
                remaining -= tokens

            tokens_in = int(tokens * rng.uniform(0.45, 0.65))
            tokens_out = tokens - tokens_in
            model = rng.choice(models)
            unit_cost = MODEL_UNIT_COSTS[model]
            timestamp = datetime.combine(
                day,
                time(hour=rng.randint(8, 22), minute=rng.randint(0, 59)),
                tzinfo=timezone.utc,
            ).isoformat().replace("+00:00", "Z")
            records.append(
                UsageRecord(
                    timestamp=timestamp,
                    model=model,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost_estimate=round(tokens * unit_cost, 4),
                    session_type=rng.choice(session_types),
                )
            )

    return records


def initialize_data_files(
    *,
    data_dir: str | Path,
    overwrite: bool = False,
    quota_config: QuotaConfig | None = None,
) -> dict:
    data_path = Path(data_dir)
    data_path.mkdir(parents=True, exist_ok=True)
    quota_path = data_path / "quota_config.json"
    usage_path = data_path / "usage_log.json"
    relay_path = data_path / "relay_requests.json"
    provider_path = data_path / "provider_pool.json"
    request_log_path = data_path / "request_log.json"

    created: list[str] = []
    config = quota_config or default_quota_config()
    if overwrite or not quota_path.exists():
        save_quota_config(quota_path, config)
        created.append(str(quota_path))
    if overwrite or not usage_path.exists():
        save_usage_log(usage_path, [])
        created.append(str(usage_path))
    if overwrite or not relay_path.exists():
        save_relay_requests(relay_path, default_relay_requests())
        created.append(str(relay_path))
    if overwrite or not provider_path.exists():
        save_provider_pool(provider_path, default_provider_pool())
        created.append(str(provider_path))
    if overwrite or not request_log_path.exists():
        save_request_log(request_log_path, [])
        created.append(str(request_log_path))
    return {"created": created, "data_dir": str(data_path)}


def write_mock_dataset(*, data_dir: str | Path, days: int = 30, seed: int = 7) -> dict:
    data_path = Path(data_dir)
    quota_path = data_path / "quota_config.json"
    usage_path = data_path / "usage_log.json"

    if quota_path.exists():
        quota = load_quota_config(quota_path)
    else:
        quota = default_quota_config()

    reference = today_utc()
    start = reference - timedelta(days=days - 1)
    records = generate_mock_records(start_date=start, days=days, seed=seed)
    cycle_start, cycle_end = cycle_dates(quota, reference)
    generated_tokens = sum(record.total_tokens for record in records)
    current_usage = sum(
        record.total_tokens
        for record in records
        if cycle_start <= parse_timestamp(record.timestamp).date() < cycle_end
    )
    save_usage_log(usage_path, records)
    save_quota_config(quota_path, quota.with_current_usage(current_usage))
    return {
        "records": len(records),
        "days": days,
        "generated_tokens": generated_tokens,
        "current_cycle_tokens": current_usage,
        "usage_log": str(usage_path),
        "quota_config": str(quota_path),
    }
