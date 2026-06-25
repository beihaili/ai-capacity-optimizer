"""End-to-end prediction report assembly."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from aco.backend.optimizer import build_optimizer_report
from aco.backend.quota_model import cycle_dates, load_quota_config
from aco.backend.relay_hub import build_relay_report
from aco.backend.usage_tracker import (
    dense_daily_history,
    latest_record_date,
    load_usage_log,
    parse_timestamp,
)
from aco.engine.forecast_engine import predict_month_end_usage
from aco.engine.idle_detection import build_idle_report
from aco.engine.value_estimator import estimate_average_unit_cost, estimate_wasted_value


DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def infer_reference_date(records, explicit_reference: date | str | None = None) -> date:
    if explicit_reference is not None:
        if isinstance(explicit_reference, date):
            return explicit_reference
        return datetime.fromisoformat(explicit_reference).date()
    today = datetime.now(timezone.utc).date()
    past_dates = []
    for record in records:
        record_date = parse_timestamp(record.timestamp).date()
        if record_date <= today:
            past_dates.append(record_date)
    if past_dates:
        return max(past_dates)
    latest = latest_record_date(records)
    return latest or today


def records_in_cycle(records, *, start: date, end: date):
    end_inclusive = end - timedelta(days=1)
    selected = []
    for record in records:
        record_date = parse_timestamp(record.timestamp).date()
        if start <= record_date <= end_inclusive:
            selected.append(record)
    return selected


def generate_prediction_report(
    *,
    data_dir: str | Path = DEFAULT_DATA_DIR,
    reference_date: date | str | None = None,
) -> dict:
    data_path = Path(data_dir)
    quota = load_quota_config(data_path / "quota_config.json")
    records = load_usage_log(data_path / "usage_log.json")
    reference = infer_reference_date(records, reference_date)
    cycle_start, cycle_end = cycle_dates(quota, reference)
    cycle_records = records_in_cycle(records, start=cycle_start, end=cycle_end)

    history_end = min(reference, cycle_end - timedelta(days=1))
    history = dense_daily_history(cycle_records, start_date=cycle_start, end_date=history_end)
    values = [item["tokens"] for item in history]
    current_usage = sum(values)
    remaining_days = max(0, (cycle_end - history_end).days - 1)

    forecast = predict_month_end_usage(
        values,
        monthly_budget_tokens=quota.monthly_budget_tokens,
        current_usage=current_usage,
        remaining_days=remaining_days,
    )
    idle = build_idle_report(
        current_usage=forecast["current_usage"],
        predicted_usage=forecast["predicted_month_end_usage"],
        quota=quota.monthly_budget_tokens,
    )
    avg_unit_cost = estimate_average_unit_cost(cycle_records)
    wasted_value = estimate_wasted_value(
        forecast["estimated_idle_tokens"],
        avg_unit_cost=avg_unit_cost,
        urgency_factor=1.0,
    )
    optimizer = build_optimizer_report(
        idle_tokens=forecast["estimated_idle_tokens"],
        idle_level=idle["idle_level"],
        usage_risk=idle["usage_risk"],
    )
    relay = build_relay_report(
        data_dir=data_path,
        available_tokens=forecast["estimated_idle_tokens"],
        reference_date=reference,
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "plan": quota.plan,
        "cycle": {
            "start": cycle_start.isoformat(),
            "end_exclusive": cycle_end.isoformat(),
            "reference_date": reference.isoformat(),
        },
        "quota": quota.to_dict(),
        "daily_history": history,
        "forecast": forecast,
        "idle": idle,
        "value": {
            "avg_unit_cost": round(avg_unit_cost, 8),
            "estimated_wasted_value": wasted_value,
        },
        "optimizer": optimizer,
        "relay": relay,
    }
