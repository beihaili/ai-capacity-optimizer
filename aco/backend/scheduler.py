"""Internal task allocation simulator."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class SimulatedTask:
    name: str
    tokens_required: int
    priority: int
    task_type: str

    def to_dict(self) -> dict:
        return asdict(self)


DEFAULT_TASKS = [
    SimulatedTask("summarize_research_backlog", 35_000, 90, "batch"),
    SimulatedTask("code_review_batch", 55_000, 80, "code"),
    SimulatedTask("doc_generation_sweep", 45_000, 70, "writing"),
    SimulatedTask("meeting_notes_cleanup", 20_000, 60, "batch"),
    SimulatedTask("prompt_library_eval", 30_000, 50, "eval"),
]


def simulate_schedule(
    available_tokens: int,
    tasks: Iterable[SimulatedTask] | None = None,
) -> dict:
    if available_tokens <= 0:
        return {
            "available_tokens": 0,
            "allocated_tokens": 0,
            "virtual_credits": 0,
            "selected_tasks": [],
            "skipped_tasks": [task.to_dict() for task in (tasks or DEFAULT_TASKS)],
        }

    selected: list[SimulatedTask] = []
    skipped: list[SimulatedTask] = []
    remaining = available_tokens
    ordered_tasks = sorted(tasks or DEFAULT_TASKS, key=lambda task: (-task.priority, task.tokens_required))

    for task in ordered_tasks:
        if task.tokens_required <= remaining:
            selected.append(task)
            remaining -= task.tokens_required
        else:
            skipped.append(task)

    allocated = available_tokens - remaining
    return {
        "available_tokens": available_tokens,
        "allocated_tokens": allocated,
        "virtual_credits": available_tokens // 1_000,
        "selected_tasks": [task.to_dict() for task in selected],
        "skipped_tasks": [task.to_dict() for task in skipped],
    }


def simple_capacity_price(*, demand_index: float, supply_index: float) -> float:
    if supply_index <= 0:
        raise ValueError("supply_index must be positive")
    if demand_index < 0:
        raise ValueError("demand_index must be non-negative")
    return round(demand_index / supply_index, 4)

