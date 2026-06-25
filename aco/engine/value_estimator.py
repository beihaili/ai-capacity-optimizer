"""Estimate the virtual value of idle capacity."""

from __future__ import annotations

from collections.abc import Iterable

from aco.backend.usage_tracker import UsageRecord


DEFAULT_UNIT_COST = 0.00001


def estimate_average_unit_cost(records: Iterable[UsageRecord], fallback: float = DEFAULT_UNIT_COST) -> float:
    total_tokens = 0
    total_cost = 0.0
    for record in records:
        total_tokens += record.total_tokens
        total_cost += record.cost_estimate
    if total_tokens <= 0 or total_cost <= 0:
        return fallback
    return total_cost / total_tokens


def estimate_wasted_value(
    idle_tokens: int,
    *,
    avg_unit_cost: float = DEFAULT_UNIT_COST,
    urgency_factor: float = 1.0,
) -> float:
    if idle_tokens <= 0:
        return 0.0
    if avg_unit_cost < 0:
        raise ValueError("avg_unit_cost must be non-negative")
    if urgency_factor < 0:
        raise ValueError("urgency_factor must be non-negative")
    return round(idle_tokens * avg_unit_cost * urgency_factor, 4)

