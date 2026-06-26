"""Command line interface for AI Capacity Optimizer."""

from __future__ import annotations

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import json
from pathlib import Path

from aco.backend.api_gateway import (
    provider_pool_summary,
    route_unified_request,
    seed_provider_pool,
    simulate_chat_completion,
)
from aco.backend.mock_data import initialize_data_files, write_mock_dataset
from aco.backend.predictor import DEFAULT_DATA_DIR, generate_prediction_report
from aco.backend.quota_model import QuotaConfig, load_quota_config, save_quota_config
from aco.backend.relay_hub import add_relay_request, build_relay_report, seed_relay_requests
from aco.backend.usage_tracker import append_usage, load_usage_log, total_tokens
from aco.skills.registry import list_skill_payloads


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI Capacity Optimizer MVP")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="Directory containing ACO data files.")
    parser.add_argument("--skills-dir", help="Directory containing local ACO skills.")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="Create default data files.")
    init_parser.add_argument("--overwrite", action="store_true", help="Replace existing data files.")
    init_parser.add_argument("--plan", default="chatgpt_pro")
    init_parser.add_argument("--monthly-budget-tokens", type=int, default=1_000_000)
    init_parser.add_argument("--reset-day", type=int, default=1)
    init_parser.add_argument("--billing-cycle-start", default="2026-06-01")

    mock_parser = subparsers.add_parser("mock", help="Generate mock usage data.")
    mock_parser.add_argument("--days", type=int, default=30)
    mock_parser.add_argument("--seed", type=int, default=7)

    log_parser = subparsers.add_parser("log", help="Append one usage event.")
    log_parser.add_argument("--model", required=True)
    log_parser.add_argument("--tokens-in", type=int, required=True)
    log_parser.add_argument("--tokens-out", type=int, required=True)
    log_parser.add_argument("--cost-estimate", type=float, default=0.0)
    log_parser.add_argument("--session-type", choices=["chat", "api", "batch"], default="chat")
    log_parser.add_argument("--timestamp")

    report_parser = subparsers.add_parser("report", help="Print a prediction report.")
    report_parser.add_argument("--reference-date")
    report_parser.add_argument("--output", help="Optional JSON output path.")

    relay_seed_parser = subparsers.add_parser("relay-seed", help="Create default relay hub requests.")
    relay_seed_parser.add_argument("--overwrite", action="store_true", help="Replace existing relay requests.")

    relay_add_parser = subparsers.add_parser("relay-add", help="Add one relay hub request.")
    relay_add_parser.add_argument("--source", required=True)
    relay_add_parser.add_argument("--title", required=True)
    relay_add_parser.add_argument("--requested-tokens", type=int, required=True)
    relay_add_parser.add_argument("--priority", type=int, default=50)
    relay_add_parser.add_argument("--deadline", required=True)
    relay_add_parser.add_argument("--min-tokens", type=int)
    relay_add_parser.add_argument("--tag", action="append", default=[])

    relay_plan_parser = subparsers.add_parser("relay-plan", help="Print a relay hub allocation plan.")
    relay_plan_parser.add_argument("--available-tokens", type=int, help="Override available tokens.")
    relay_plan_parser.add_argument("--reference-date")

    provider_seed_parser = subparsers.add_parser("provider-seed", help="Create default unified API providers.")
    provider_seed_parser.add_argument("--overwrite", action="store_true", help="Replace existing provider pool.")

    subparsers.add_parser("provider-list", help="Print unified API provider capacity.")

    api_route_parser = subparsers.add_parser("api-route", help="Route one unified API request.")
    api_route_parser.add_argument("--prompt", required=True)
    api_route_parser.add_argument("--estimated-tokens", type=int)
    api_route_parser.add_argument("--policy", choices=["balanced", "quality", "cheap", "fast", "fill_idle"], default="balanced")

    api_complete_parser = subparsers.add_parser("api-complete", help="Simulate one unified chat completion.")
    api_complete_parser.add_argument("--prompt", required=True)
    api_complete_parser.add_argument("--estimated-tokens", type=int)
    api_complete_parser.add_argument("--max-tokens", type=int, default=256)
    api_complete_parser.add_argument("--policy", choices=["balanced", "quality", "cheap", "fast", "fill_idle"], default="balanced")
    api_complete_parser.add_argument("--debug", action="store_true")
    api_complete_parser.add_argument("--live", action="store_true", help="Call a real OpenAI-compatible provider.")

    serve_api_parser = subparsers.add_parser("serve-api", help="Start the local unified API server.")
    serve_api_parser.add_argument("--host", default="127.0.0.1")
    serve_api_parser.add_argument("--port", type=int, default=8787)
    serve_api_parser.add_argument("--live", action="store_true", help="Forward chat completions to real providers.")

    subparsers.add_parser("skills-list", help="List local ACO skills.")

    subparsers.add_parser("sync-quota", help="Sync quota current_usage from usage log.")
    return parser


def handle_init(args: argparse.Namespace) -> dict:
    quota = QuotaConfig(
        plan=args.plan,
        monthly_budget_tokens=args.monthly_budget_tokens,
        reset_day=args.reset_day,
        current_usage=0,
        billing_cycle_start=args.billing_cycle_start,
    )
    return initialize_data_files(data_dir=args.data_dir, overwrite=args.overwrite, quota_config=quota)


def handle_log(args: argparse.Namespace) -> dict:
    data_dir = Path(args.data_dir)
    usage_path = data_dir / "usage_log.json"
    quota_path = data_dir / "quota_config.json"
    record = append_usage(
        usage_path,
        model=args.model,
        tokens_in=args.tokens_in,
        tokens_out=args.tokens_out,
        cost_estimate=args.cost_estimate,
        session_type=args.session_type,
        timestamp=args.timestamp,
    )
    quota = load_quota_config(quota_path)
    records = load_usage_log(usage_path)
    save_quota_config(quota_path, quota.with_current_usage(total_tokens(records)))
    return {"record": record.to_dict(), "current_usage": total_tokens(records)}


def handle_report(args: argparse.Namespace) -> dict:
    report = generate_prediction_report(data_dir=args.data_dir, reference_date=args.reference_date)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def handle_relay_seed(args: argparse.Namespace) -> dict:
    return seed_relay_requests(data_dir=args.data_dir, overwrite=args.overwrite)


def handle_relay_add(args: argparse.Namespace) -> dict:
    request = add_relay_request(
        data_dir=args.data_dir,
        source=args.source,
        title=args.title,
        requested_tokens=args.requested_tokens,
        priority=args.priority,
        deadline=args.deadline,
        min_tokens=args.min_tokens,
        tags=args.tag,
    )
    return {"request": request.to_dict()}


def handle_relay_plan(args: argparse.Namespace) -> dict:
    if args.available_tokens is not None:
        available_tokens = args.available_tokens
    else:
        report = generate_prediction_report(data_dir=args.data_dir, reference_date=args.reference_date)
        available_tokens = report["forecast"]["estimated_idle_tokens"]
    return build_relay_report(
        data_dir=args.data_dir,
        available_tokens=available_tokens,
        reference_date=args.reference_date,
    )


def handle_provider_seed(args: argparse.Namespace) -> dict:
    return seed_provider_pool(data_dir=args.data_dir, overwrite=args.overwrite)


def handle_provider_list(args: argparse.Namespace) -> dict:
    return provider_pool_summary(data_dir=args.data_dir)


def handle_api_route(args: argparse.Namespace) -> dict:
    payload = {
        "prompt": args.prompt,
        "policy": args.policy,
    }
    if args.estimated_tokens is not None:
        payload["estimated_tokens"] = args.estimated_tokens
    return route_unified_request(data_dir=args.data_dir, payload=payload, skills_dir=args.skills_dir)


def handle_api_complete(args: argparse.Namespace) -> dict:
    payload = {
        "messages": [{"role": "user", "content": args.prompt}],
        "max_tokens": args.max_tokens,
        "policy": args.policy,
        "debug": args.debug,
        "live": args.live,
    }
    if args.estimated_tokens is not None:
        payload["estimated_tokens"] = args.estimated_tokens
    return simulate_chat_completion(data_dir=args.data_dir, payload=payload, skills_dir=args.skills_dir, live=args.live)


def handle_serve_api(args: argparse.Namespace) -> int:
    from aco.api_server import run_server

    run_server(host=args.host, port=args.port, data_dir=args.data_dir, skills_dir=args.skills_dir, live=args.live)
    return 0


def handle_skills_list(args: argparse.Namespace) -> dict:
    return {"skills": list_skill_payloads(args.skills_dir)}


def handle_sync_quota(args: argparse.Namespace) -> dict:
    data_dir = Path(args.data_dir)
    usage_path = data_dir / "usage_log.json"
    quota_path = data_dir / "quota_config.json"
    quota = load_quota_config(quota_path)
    records = load_usage_log(usage_path)
    current_usage = total_tokens(records)
    save_quota_config(quota_path, quota.with_current_usage(current_usage))
    return {"current_usage": current_usage, "quota_config": str(quota_path)}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = args.command or "report"

    if command == "init":
        payload = handle_init(args)
    elif command == "mock":
        payload = write_mock_dataset(data_dir=args.data_dir, days=args.days, seed=args.seed)
    elif command == "log":
        payload = handle_log(args)
    elif command == "report":
        payload = handle_report(args)
    elif command == "relay-seed":
        payload = handle_relay_seed(args)
    elif command == "relay-add":
        payload = handle_relay_add(args)
    elif command == "relay-plan":
        payload = handle_relay_plan(args)
    elif command == "provider-seed":
        payload = handle_provider_seed(args)
    elif command == "provider-list":
        payload = handle_provider_list(args)
    elif command == "api-route":
        payload = handle_api_route(args)
    elif command == "api-complete":
        payload = handle_api_complete(args)
    elif command == "serve-api":
        return handle_serve_api(args)
    elif command == "skills-list":
        payload = handle_skills_list(args)
    elif command == "sync-quota":
        payload = handle_sync_quota(args)
    else:
        parser.error(f"unknown command: {command}")
        return 2

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
