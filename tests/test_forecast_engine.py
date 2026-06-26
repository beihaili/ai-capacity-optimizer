from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from aco.backend.api_gateway import ProviderConfig, route_unified_request, save_provider_pool, score_candidates, simulate_chat_completion
from aco.backend.openai_compatible import ProviderCallError
from aco.backend.quota_model import QuotaConfig, save_quota_config
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

    def test_live_completion_falls_back_and_records_usage(self) -> None:
        with TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            save_quota_config(
                data_dir / "quota_config.json",
                QuotaConfig(
                    plan="personal",
                    monthly_budget_tokens=100_000,
                    reset_day=1,
                    current_usage=0,
                    billing_cycle_start="2026-06-01",
                ),
            )
            save_provider_pool(
                data_dir / "provider_pool.json",
                [
                    ProviderConfig(
                        provider_id="primary",
                        provider="openai_compatible",
                        model="gpt-4o",
                        monthly_budget_tokens=100_000,
                        current_usage=0,
                        quality_score=0.99,
                        latency_ms=500,
                        cost_per_1k_tokens=0.01,
                        base_url="https://primary.example.com/v1",
                        api_key_env="ACO_PRIMARY_KEY",
                    ),
                    ProviderConfig(
                        provider_id="backup",
                        provider="openai_compatible",
                        model="gpt-4o-mini",
                        monthly_budget_tokens=100_000,
                        current_usage=0,
                        quality_score=0.80,
                        latency_ms=700,
                        cost_per_1k_tokens=0.002,
                        base_url="https://backup.example.com/v1",
                        api_key_env="ACO_BACKUP_KEY",
                    ),
                ],
            )

            def fake_call(provider: dict, payload: dict) -> dict:
                if provider["provider_id"] == "primary":
                    raise ProviderCallError("temporary failure", code="provider_http_error", status=500)
                return {
                    "id": "chatcmpl-test",
                    "object": "chat.completion",
                    "created": 123,
                    "model": provider["model"],
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": "ok"},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7},
                }

            with patch("aco.backend.api_gateway.call_openai_compatible", side_effect=fake_call):
                response = simulate_chat_completion(
                    data_dir=data_dir,
                    payload={
                        "messages": [{"role": "user", "content": "hello"}],
                        "policy": "quality",
                        "live": True,
                        "debug": True,
                    },
                    live=True,
                )

            self.assertEqual(response["model"], "gpt-4o-mini")
            self.assertEqual(response["usage"]["total_tokens"], 7)
            self.assertEqual(response["aco"]["live_attempts"][0]["status"], "failed")
            self.assertEqual(response["aco"]["live_attempts"][1]["status"], "success")

            request_log = json.loads((data_dir / "request_log.json").read_text(encoding="utf-8"))
            self.assertEqual([item["status"] for item in request_log], ["failed", "success"])
            usage_log = json.loads((data_dir / "usage_log.json").read_text(encoding="utf-8"))
            self.assertEqual(usage_log[0]["tokens_in"], 3)
            self.assertEqual(usage_log[0]["tokens_out"], 4)


if __name__ == "__main__":
    unittest.main()
