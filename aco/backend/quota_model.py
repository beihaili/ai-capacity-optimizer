"""Quota configuration and billing-cycle helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
import calendar
import json
from pathlib import Path


@dataclass(frozen=True)
class QuotaConfig:
    plan: str
    monthly_budget_tokens: int
    reset_day: int
    current_usage: int
    billing_cycle_start: str

    @classmethod
    def from_dict(cls, data: dict) -> "QuotaConfig":
        config = cls(
            plan=str(data.get("plan", "chatgpt_pro")),
            monthly_budget_tokens=int(data["monthly_budget_tokens"]),
            reset_day=int(data.get("reset_day", 1)),
            current_usage=int(data.get("current_usage", 0)),
            billing_cycle_start=str(data["billing_cycle_start"]),
        )
        config.validate()
        return config

    def to_dict(self) -> dict:
        return asdict(self)

    def validate(self) -> None:
        if not self.plan:
            raise ValueError("plan is required")
        if self.monthly_budget_tokens <= 0:
            raise ValueError("monthly_budget_tokens must be positive")
        if not 1 <= self.reset_day <= 31:
            raise ValueError("reset_day must be between 1 and 31")
        if self.current_usage < 0:
            raise ValueError("current_usage must be non-negative")
        parse_date(self.billing_cycle_start)

    def with_current_usage(self, current_usage: int) -> "QuotaConfig":
        return QuotaConfig(
            plan=self.plan,
            monthly_budget_tokens=self.monthly_budget_tokens,
            reset_day=self.reset_day,
            current_usage=max(0, int(current_usage)),
            billing_cycle_start=self.billing_cycle_start,
        )


def parse_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(value).date()


def today_utc() -> date:
    return datetime.now(timezone.utc).date()


def clamp_day(year: int, month: int, day: int) -> int:
    return min(day, calendar.monthrange(year, month)[1])


def shift_month(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = clamp_day(year, month, value.day)
    return date(year, month, day)


def infer_cycle_dates(reset_day: int, reference_date: date) -> tuple[date, date]:
    current_reset = date(
        reference_date.year,
        reference_date.month,
        clamp_day(reference_date.year, reference_date.month, reset_day),
    )
    if reference_date >= current_reset:
        start = current_reset
        end = shift_month(start, 1)
    else:
        end = current_reset
        start = shift_month(end, -1)
    return start, end


def cycle_dates(config: QuotaConfig, reference_date: date | str | None = None) -> tuple[date, date]:
    reference = parse_date(reference_date) if reference_date is not None else today_utc()
    configured_start = parse_date(config.billing_cycle_start)
    configured_end = shift_month(configured_start, 1)
    if configured_start <= reference < configured_end:
        return configured_start, configured_end
    return infer_cycle_dates(config.reset_day, reference)


def load_quota_config(path: str | Path) -> QuotaConfig:
    config_path = Path(path)
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    return QuotaConfig.from_dict(raw)


def save_quota_config(path: str | Path, config: QuotaConfig) -> None:
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")


def default_quota_config(reference_date: date | None = None) -> QuotaConfig:
    reference = reference_date or today_utc()
    cycle_start = date(reference.year, reference.month, 1)
    return QuotaConfig(
        plan="chatgpt_pro",
        monthly_budget_tokens=1_000_000,
        reset_day=1,
        current_usage=0,
        billing_cycle_start=cycle_start.isoformat(),
    )

