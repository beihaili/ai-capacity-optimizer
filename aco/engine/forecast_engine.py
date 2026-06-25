"""Forecasting utilities for quota usage."""

from __future__ import annotations

from collections.abc import Sequence


def exponential_moving_average(values: Sequence[float], alpha: float = 0.35) -> float:
    if not values:
        return 0.0
    if not 0 < alpha <= 1:
        raise ValueError("alpha must be in the interval (0, 1]")

    ema = float(values[0])
    for value in values[1:]:
        ema = alpha * float(value) + (1 - alpha) * ema
    return ema


def linear_regression_slope(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0

    n = len(values)
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    numerator = sum((idx - x_mean) * (float(value) - y_mean) for idx, value in enumerate(values))
    denominator = sum((idx - x_mean) ** 2 for idx in range(n))
    return numerator / denominator if denominator else 0.0


def predict_daily_usage(values: Sequence[float], *, alpha: float = 0.35, trend_window: int = 7) -> dict:
    if not values:
        return {
            "ema_daily_usage": 0.0,
            "trend_tokens_per_day": 0.0,
            "predicted_daily_usage": 0.0,
        }

    base = exponential_moving_average(values, alpha=alpha)
    trend_values = values[-trend_window:] if trend_window > 0 else values
    trend = linear_regression_slope(trend_values)
    predicted_daily = max(0.0, base + trend)
    return {
        "ema_daily_usage": round(base, 2),
        "trend_tokens_per_day": round(trend, 2),
        "predicted_daily_usage": round(predicted_daily, 2),
    }


def predict_month_end_usage(
    daily_history: Sequence[float],
    *,
    monthly_budget_tokens: int,
    current_usage: int | None = None,
    remaining_days: int = 0,
    alpha: float = 0.35,
    trend_window: int = 7,
) -> dict:
    if monthly_budget_tokens <= 0:
        raise ValueError("monthly_budget_tokens must be positive")
    if remaining_days < 0:
        raise ValueError("remaining_days must be non-negative")

    usage_to_date = int(sum(daily_history)) if current_usage is None else int(current_usage)
    daily = predict_daily_usage(daily_history, alpha=alpha, trend_window=trend_window)
    predicted_remaining = daily["predicted_daily_usage"] * remaining_days
    predicted_total = usage_to_date + predicted_remaining
    idle_tokens = max(0, monthly_budget_tokens - predicted_total)
    overage_tokens = max(0, predicted_total - monthly_budget_tokens)

    return {
        "monthly_budget_tokens": monthly_budget_tokens,
        "current_usage": usage_to_date,
        "usage_percent": round((usage_to_date / monthly_budget_tokens) * 100, 2),
        "ema_daily_usage": daily["ema_daily_usage"],
        "trend_tokens_per_day": daily["trend_tokens_per_day"],
        "predicted_daily_usage": daily["predicted_daily_usage"],
        "remaining_days": remaining_days,
        "predicted_remaining_usage": int(round(predicted_remaining)),
        "predicted_month_end_usage": int(round(predicted_total)),
        "predicted_month_end_percent": round((predicted_total / monthly_budget_tokens) * 100, 2),
        "estimated_idle_tokens": int(round(idle_tokens)),
        "overage_tokens": int(round(overage_tokens)),
    }

