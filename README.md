# AI Capacity Optimizer

AI Capacity Optimizer, or ACO, is a forecasting and optimization layer for existing LLM gateways. It predicts AI quota usage, detects idle capacity, and recommends work that can use otherwise wasted budget.

ACO is not trying to replace mature gateways such as LiteLLM, New API, or one-api. It is designed to sit above them as a local, inspectable quota intelligence layer.

## What It Does

1. Observation: record usage events and daily token totals.
2. Forecasting: estimate month-end usage with EMA plus a short trend.
3. Decisioning: flag idle or over-quota risk and suggest actions.
4. Relay hub: turn idle capacity into internal task requests.
5. Gateway compatibility: read from and optionally proxy OpenAI-compatible gateways.
6. Local skills: let routing policies be extended from the `skills/` directory.

## Status

ACO is alpha software. The default provider calls are simulated so the project can be tested without real API keys, private account data, or billing integration.

## Request For Feedback

ACO is looking for feedback from people who run LiteLLM, New API, one-api, OpenRouter relays, or shared AI API budgets. The current question is whether imported usage data plus a month-end forecast helps teams predict idle capacity, overrun risk, and useful batch work before quota resets.

Start here: [Feedback](docs/feedback.md)

## Quick Start

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
aco init
aco mock --days 30 --seed 7
aco report
aco relay-plan
aco skills-list
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

## Compatibility API Quick Test

ACO includes a small local API for demos and compatibility testing. This is not intended to compete with full gateway projects.

```bash
aco serve-api --port 8787
```

Call the local endpoint:

```bash
curl --noproxy '*' http://127.0.0.1:8787/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Give me the best answer through one API."}],"policy":"balanced"}'
```

Add `"debug": true` to inspect the routing decision.

## Use With Existing Gateways

The recommended production shape is to run ACO next to an existing gateway:

- [LiteLLM](https://github.com/BerriAI/litellm) for OpenAI-compatible access, provider routing, budgets, spend logs, and load balancing.
- [New API](https://github.com/QuantumNous/new-api) or [one-api](https://github.com/songquanpeng/one-api) for model aggregation, quota, key distribution, and Chinese relay scenarios.
- [Langfuse](https://github.com/langfuse/langfuse) or [Helicone](https://github.com/Helicone/helicone) for tracing, observability, and analytics.

ACO's job is to import usage and quota data from these systems, predict month-end waste or overrun, and produce optimization recommendations.

The longer-term goal is upstream-friendly integration: build connectors and reports in ACO, then contribute small PRs back to gateway projects when they need export hooks, docs, or compatibility helpers.

## Local Skills

ACO can load local skills from the `skills/` directory. The first supported skill type is `routing_policy`, which can reorder provider candidates before the unified API selects a backend.

```bash
aco skills-list
aco api-complete --prompt "Use idle capacity" --policy fill_idle --debug
```

## Data Files

- `aco/data/usage_log.json`: usage events.
- `aco/data/quota_config.json`: plan and quota settings.
- `aco/data/relay_requests.json`: internal requests that can consume idle capacity.
- `aco/data/provider_pool.json`: provider and model pools behind the unified API.
- `aco/data/request_log.json`: unified API attempts, fallback status, latency, and cost estimates.

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

The unified API is a compatibility layer for local demos. For production gateway behavior, prefer LiteLLM, New API, or one-api, then let ACO consume their usage, budget, and quota data.

```bash
aco provider-list
aco api-route --prompt "Explain today's capacity state" --policy balanced
aco api-complete --prompt "Explain today's capacity state" --debug
aco serve-api --port 8787
```

To call a real OpenAI-compatible relay, edit `aco/data/provider_pool.json`, enable the `personal-relay` provider, set its `base_url`, then export the API key named by `api_key_env`.

```bash
export ACO_RELAY_API_KEY="..."
aco api-complete --live --prompt "Explain today's capacity state" --debug
aco serve-api --live --port 8787
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
- [Gateway Integration Roadmap](docs/gateway-integration-roadmap.md)
- [Upstream PR Strategy](docs/upstream-pr-strategy.md)
- [LiteLLM Phase 0 Upstream Discovery](docs/upstream/litellm-phase-0-discovery.md)
- [Skills](docs/skills.md)
- [Related Projects](docs/alternatives.md)
- [Roadmap](ROADMAP.md)
- [Contributing](CONTRIBUTING.md)
- [GitHub Actions CI](.github/workflows/ci.yml)
