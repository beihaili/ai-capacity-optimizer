# AI Capacity Optimizer

AI Capacity Optimizer, or ACO, is a local MVP for forecasting AI quota usage, detecting idle capacity, routing internal work, and hiding multiple AI provider pools behind one unified API.

The first version intentionally avoids real account integration and real trading. It is designed as a local, inspectable product prototype for AI usage optimization.

## What It Does

1. Observation: record usage events and daily token totals.
2. Forecasting: estimate month-end usage with EMA plus a short trend.
3. Decisioning: flag idle or over-quota risk and suggest actions.
4. Relay hub: route idle capacity into internal task requests.
5. Unified API: hide multiple providers behind one user-facing endpoint.

## Status

ACO is alpha software. The default provider calls are simulated so the project can be tested without real API keys, private account data, or billing integration.

## Quick Start

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
aco init
aco mock --days 30 --seed 7
aco report
aco relay-plan
aco api-complete --prompt "Summarize my quota risk" --debug
```

Optional dashboard:

```bash
streamlit run aco/frontend/dashboard.py
```

Run tests:

```bash
python -m unittest
```

## Unified API Quick Test

Start the local API:

```bash
aco serve-api --port 8787
```

Call the single user-facing endpoint:

```bash
curl --noproxy '*' http://127.0.0.1:8787/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Give me the best answer through one API."}],"policy":"balanced"}'
```

Add `"debug": true` to inspect the routing decision.

## Data Files

- `aco/data/usage_log.json`: usage events.
- `aco/data/quota_config.json`: plan and quota settings.
- `aco/data/relay_requests.json`: internal requests that can consume idle capacity.
- `aco/data/provider_pool.json`: provider and model pools behind the unified API.

`usage_log.json` is stored as a list of usage records. The loader also accepts a single-object JSON file for compatibility with early examples.

## Relay Hub

The relay hub is the local middle station for the MVP. It accepts internal requests, ranks active requests by priority and deadline, then allocates predicted idle tokens.

```bash
python -m aco.main relay-seed --overwrite
python -m aco.main relay-add \
  --source research-agent \
  --title "Summarize old notes" \
  --requested-tokens 50000 \
  --min-tokens 20000 \
  --priority 80 \
  --deadline 2026-06-28 \
  --tag research
python -m aco.main relay-plan
```

## Unified API

The unified API is the user-facing layer. Clients call one endpoint while ACO chooses a provider/model pool based on policy, quality, cost, latency, and remaining capacity.

```bash
aco provider-list
aco api-route --prompt "Explain today's capacity state" --policy balanced
aco api-complete --prompt "Explain today's capacity state" --debug
aco serve-api --port 8787
```

HTTP endpoints:

- `GET /health`
- `GET /v1/capacity`
- `POST /v1/route`
- `POST /v1/chat/completions`

Example request:

```bash
curl --noproxy '*' http://127.0.0.1:8787/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Summarize my capacity risk"}],"policy":"balanced","debug":true}'
```

## Documentation

- [Architecture](docs/architecture.md)
- [API](docs/api.md)
- [Roadmap](ROADMAP.md)
- [Contributing](CONTRIBUTING.md)
- [GitHub Actions CI](.github/workflows/ci.yml)
