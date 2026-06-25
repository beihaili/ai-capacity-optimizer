"""Idle quota and usage risk classification."""

from __future__ import annotations


def detect_idle_quota(
    *,
    current_usage: int,
    predicted_usage: int,
    quota: int,
) -> str:
    if quota <= 0:
        raise ValueError("quota must be positive")

    ratio = predicted_usage / quota
    if ratio < 0.8:
        return "HIGH_IDLE"
    if ratio < 1.0:
        return "MEDIUM_IDLE"
    return "NO_IDLE"


def idle_risk_level(idle_level: str) -> str:
    mapping = {
        "HIGH_IDLE": "red",
        "MEDIUM_IDLE": "yellow",
        "NO_IDLE": "green",
    }
    return mapping.get(idle_level, "yellow")


def usage_risk_level(*, predicted_usage: int, quota: int) -> str:
    if quota <= 0:
        raise ValueError("quota must be positive")

    ratio = predicted_usage / quota
    if ratio >= 1.0:
        return "red"
    if ratio >= 0.85:
        return "yellow"
    return "green"


def build_idle_report(*, current_usage: int, predicted_usage: int, quota: int) -> dict:
    idle_level = detect_idle_quota(
        current_usage=current_usage,
        predicted_usage=predicted_usage,
        quota=quota,
    )
    return {
        "idle_level": idle_level,
        "idle_risk": idle_risk_level(idle_level),
        "usage_risk": usage_risk_level(predicted_usage=predicted_usage, quota=quota),
    }

