from __future__ import annotations

import unittest

from aco.backend.api_gateway import ProviderConfig, route_unified_request, score_candidates
from aco.backend.scheduler import simulate_schedule
from aco.backend.relay_hub import RelayRequest, allocate_capacity
from aco.engine.forecast_engine import (
    exponential_moving_average,
    linear_regression_slope,
    predict_month_end_usage,
)
from aco.engine.idle_detection import build_idle_report
from aco.engine.value_estimator import estimate_wasted_value
from aco.skills.registry import discover_skills


class ForecastEngineTests(unittest.TestCase):
    def test_ema_weights_recent_values(self) -> None:
        self.assertAlmostEqual(exponential_moving_average([10, 20, 30], alpha=0.5), 22.5)

    def test_linear_regression_slope_detects_trend(self) -> None:
        self.assertAlmostEqual(linear_regression_slope([10, 20, 30, 40]), 10.0)

    def test_prediction_identifies_high_idle(self) -> None:
        forecast = predict_month_end_usage(
            [10_000, 11_000, 9_000],
            monthly_budget_tokens=1_000_000,
            current_usage=30_000,
            remaining_days=10,
        )
        idle = build_idle_report(
            current_usage=forecast["current_usage"],
            predicted_usage=forecast["predicted_month_end_usage"],
            quota=forecast["monthly_budget_tokens"],
        )
        self.assertEqual(idle["idle_level"], "HIGH_IDLE")
        self.assertEqual(idle["idle_risk"], "red")

    def test_value_estimator_returns_zero_without_idle_tokens(self) -> None:
        self.assertEqual(estimate_wasted_value(0), 0.0)

    def test_scheduler_respects_available_tokens(self) -> None:
        result = simulate_schedule(40_000)
        self.assertLessEqual(result["allocated_tokens"], 40_000)
        self.assertTrue(result["selected_tasks"])

    def test_relay_hub_allocates_by_priority(self) -> None:
        requests = [
            RelayRequest(
                request_id="low",
                source="docs",
                title="Low priority",
                requested_tokens=10_000,
                min_tokens=5_000,
                priority=10,
                deadline="2026-06-29",
                created_at="2026-06-24T00:00:00Z",
            ),
            RelayRequest(
                request_id="high",
                source="research",
                title="High priority",
                requested_tokens=20_000,
                min_tokens=10_000,
                priority=90,
                deadline="2026-06-29",
                created_at="2026-06-24T00:00:00Z",
            ),
        ]
        result = allocate_capacity(available_tokens=20_000, requests=requests, reference_date="2026-06-24")
        self.assertEqual(result["selected_requests"][0]["request_id"], "high")
        self.assertEqual(result["allocated_tokens"], 20_000)

    def test_relay_hub_supports_partial_allocation(self) -> None:
        requests = [
            RelayRequest(
                request_id="partial",
                source="eval",
                title="Partial request",
                requested_tokens=50_000,
                min_tokens=20_000,
                priority=80,
                deadline="2026-06-29",
                created_at="2026-06-24T00:00:00Z",
            )
        ]
        result = allocate_capacity(available_tokens=30_000, requests=requests, reference_date="2026-06-24")
        self.assertEqual(result["selected_requests"][0]["outcome"], "partial")
        self.assertEqual(result["selected_requests"][0]["allocated_tokens"], 30_000)

    def test_unified_api_cheap_policy_prefers_low_cost_provider(self) -> None:
        providers = [
            ProviderConfig(
                provider_id="expensive",
                provider="openai",
                model="gpt-4o",
                monthly_budget_tokens=100_000,
                current_usage=10_000,
                quality_score=0.98,
                latency_ms=900,
                cost_per_1k_tokens=0.02,
            ),
            ProviderConfig(
                provider_id="cheap",
                provider="openrouter",
                model="gpt-4o-mini",
                monthly_budget_tokens=100_000,
                current_usage=10_000,
                quality_score=0.75,
                latency_ms=700,
                cost_per_1k_tokens=0.002,
            ),
        ]
        scored = score_candidates(providers, estimated_tokens=5_000, policy="cheap")
        self.assertEqual(scored[0]["provider"]["provider_id"], "cheap")

    def test_unified_api_excludes_capacity_short_provider(self) -> None:
        providers = [
            ProviderConfig(
                provider_id="full",
                provider="openai",
                model="gpt-4o",
                monthly_budget_tokens=10_000,
                current_usage=9_500,
                quality_score=0.99,
                latency_ms=900,
                cost_per_1k_tokens=0.01,
            ),
            ProviderConfig(
                provider_id="available",
                provider="anthropic",
                model="claude-3-5-sonnet",
                monthly_budget_tokens=100_000,
                current_usage=10_000,
                quality_score=0.90,
                latency_ms=1_000,
                cost_per_1k_tokens=0.012,
            ),
        ]
        scored = score_candidates(providers, estimated_tokens=5_000, policy="quality")
        self.assertEqual(len(scored), 1)
        self.assertEqual(scored[0]["provider"]["provider_id"], "available")

    def test_local_skills_are_discovered(self) -> None:
        skills = discover_skills("skills", skill_type="routing_policy")
        names = {item["manifest"].name for item in skills}
        self.assertIn("route_fill_idle", names)
        self.assertIn("route_cheap", names)

    def test_fill_idle_policy_uses_routing_skill(self) -> None:
        route = route_unified_request(
            data_dir="aco/data",
            payload={
                "prompt": "Use idle capacity",
                "policy": "fill_idle",
                "estimated_tokens": 1_000,
            },
            skills_dir="skills",
        )
        self.assertEqual(route["routing_skill"]["name"], "route_fill_idle")
        self.assertEqual(route["selected"]["provider"]["provider_id"], "cheap-batch-pool")


if __name__ == "__main__":
    unittest.main()
