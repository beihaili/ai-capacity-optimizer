"""Rule-based optimization suggestions."""

from __future__ import annotations

from aco.backend.scheduler import simulate_schedule


def generate_suggestions(*, idle_level: str, usage_risk: str) -> list[str]:
    if usage_risk == "red":
        return [
            "Pause non-urgent batch jobs until the next reset.",
            "Route low-value work to cheaper or smaller models.",
            "Reserve remaining quota for interactive and production tasks.",
        ]

    if usage_risk == "yellow":
        return [
            "Cap optional batch jobs and monitor usage daily.",
            "Move summarization and draft generation to off-peak windows.",
            "Review high-token sessions for prompt or context trimming.",
        ]

    if idle_level == "HIGH_IDLE":
        return [
            "Increase automated summarization, cleanup, and code generation tasks.",
            "Enable Task Injection Mode for low-risk backlog work.",
            "Allocate idle capacity to internal evaluation or documentation jobs.",
        ]

    if idle_level == "MEDIUM_IDLE":
        return [
            "Schedule flexible batch tasks before the quota reset.",
            "Keep a buffer for interactive work while filling predictable idle capacity.",
        ]

    return ["No optimization needed."]


def build_optimizer_report(*, idle_tokens: int, idle_level: str, usage_risk: str) -> dict:
    return {
        "suggestions": generate_suggestions(idle_level=idle_level, usage_risk=usage_risk),
        "task_injection": simulate_schedule(idle_tokens),
    }

