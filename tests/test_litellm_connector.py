from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from aco.backend.predictor import generate_prediction_report
from aco.backend.quota_model import QuotaConfig, load_quota_config, save_quota_config
from aco.backend.usage_tracker import load_usage_log
from aco.connectors.litellm import normalize_litellm_dashboard_export_row, normalize_litellm_spend_log
from aco.main import main


class LiteLLMConnectorTests(unittest.TestCase):
    def test_litellm_spend_log_normalizes_to_usage_record(self) -> None:
        record = normalize_litellm_spend_log(
            {
                "request_id": "req_mock_001",
                "model": "gpt-4o-mini",
                "call_type": "completion",
                "spend": 0.0123,
                "prompt_tokens": 1800,
                "completion_tokens": 1000,
                "startTime": "2026-06-24T12:00:00Z",
            }
        )

        self.assertEqual(record.timestamp, "2026-06-24T12:00:00Z")
        self.assertEqual(record.model, "gpt-4o-mini")
        self.assertEqual(record.tokens_in, 1800)
        self.assertEqual(record.tokens_out, 1000)
        self.assertEqual(record.cost_estimate, 0.0123)
        self.assertEqual(record.session_type, "api")

    def test_litellm_dashboard_export_row_normalizes_to_usage_record(self) -> None:
        record = normalize_litellm_dashboard_export_row(
            {
                "Date": "2026-06-24",
                "Model": "gpt-4o-mini",
                "Spend ($)": "1,234.50",
                "Total Tokens": "2,800",
            }
        )

        self.assertEqual(record.timestamp, "2026-06-24T00:00:00Z")
        self.assertEqual(record.model, "gpt-4o-mini")
        self.assertEqual(record.tokens_in, 2800)
        self.assertEqual(record.tokens_out, 0)
        self.assertEqual(record.cost_estimate, 1234.5)
        self.assertEqual(record.session_type, "api")

    def test_import_litellm_cli_writes_usage_and_forecast_runs(self) -> None:
        with TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            save_quota_config(
                data_dir / "quota_config.json",
                QuotaConfig(
                    plan="litellm_mock",
                    monthly_budget_tokens=100_000,
                    reset_day=1,
                    current_usage=0,
                    billing_cycle_start="2026-06-01",
                ),
            )

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--data-dir",
                        str(data_dir),
                        "import-litellm",
                        "--spend-log",
                        "examples/litellm_spend_logs.json",
                        "--budget",
                        "examples/litellm_budget.json",
                    ]
                )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["source"], "litellm")
            self.assertEqual(payload["imported_records"], 3)
            self.assertEqual(payload["imported_tokens"], 23800)
            self.assertEqual(payload["budget"]["max_budget"], 50.0)

            records = load_usage_log(data_dir / "usage_log.json")
            self.assertEqual(len(records), 3)
            self.assertEqual(records[2].session_type, "batch")
            self.assertEqual(load_quota_config(data_dir / "quota_config.json").current_usage, 23800)

            report = generate_prediction_report(data_dir=data_dir, reference_date="2026-06-26")
            self.assertEqual(report["forecast"]["current_usage"], 23800)
            self.assertEqual(report["forecast"]["monthly_budget_tokens"], 100_000)

    def test_import_litellm_dashboard_export_forecast_runs(self) -> None:
        with TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            save_quota_config(
                data_dir / "quota_config.json",
                QuotaConfig(
                    plan="litellm_dashboard_mock",
                    monthly_budget_tokens=100_000,
                    reset_day=1,
                    current_usage=0,
                    billing_cycle_start="2026-06-01",
                ),
            )

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--data-dir",
                        str(data_dir),
                        "import-litellm",
                        "--spend-log",
                        "examples/litellm_dashboard_daily_with_models_export.json",
                    ]
                )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["detected_shapes"], ["dashboard_export"])
            self.assertEqual(payload["imported_records"], 3)
            self.assertEqual(payload["imported_tokens"], 23800)

            records = load_usage_log(data_dir / "usage_log.json")
            self.assertEqual(records[0].timestamp, "2026-06-24T00:00:00Z")
            self.assertEqual(records[1].model, "gpt-4o")
            self.assertEqual(records[2].tokens_in, 15000)
            self.assertEqual(load_quota_config(data_dir / "quota_config.json").current_usage, 23800)

            report = generate_prediction_report(data_dir=data_dir, reference_date="2026-06-26")
            self.assertEqual(report["forecast"]["current_usage"], 23800)


if __name__ == "__main__":
    unittest.main()
