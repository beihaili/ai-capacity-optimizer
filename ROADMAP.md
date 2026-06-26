# Roadmap

## Current MVP

- Local quota forecasting.
- Idle quota detection.
- Relay hub simulation.
- Unified API compatibility simulation.
- Streamlit dashboard.
- Local routing skills.
- OpenAI-compatible live relay with fallback accounting as a compatibility layer.

## Core Direction

ACO should not compete head-on with mature LLM gateways. The main product path is:

1. Gateway Connector.
2. Forecast Engine.
3. Idle Capacity Optimizer.
4. Recommendation and Automation Layer.
5. Upstream PR Loop.

## Next

- Use the documented [LiteLLM Phase 0 Upstream Discovery](docs/upstream/litellm-phase-0-discovery.md) packet as the first connector milestone.
- Start each connector with upstream discovery: identify contribution rules, export surfaces, test fixtures, and likely maintainer-friendly PR shape.
- LiteLLM connector first: import spend logs, budgets, keys, model usage, and daily usage history.
- Ship a LiteLLM upstream PR packet alongside the connector: export example, docs patch, mock data, and forecast command.
- New API and one-api connectors next: import quota, user/channel usage, and billing logs.
- Ship New API and one-api upstream PR packets for quota or billing export docs/helpers.
- Normalize all gateway imports into ACO usage records.
- Generate month-end usage, idle-capacity, and overrun forecasts from imported gateway data.
- Produce optimization recommendations for batch jobs, summaries, code reviews, and eval workloads.
- Use connector work to identify small upstream PRs for gateway export hooks, docs, examples, and compatibility helpers.
- Keep the local OpenAI-compatible API as a demo and fallback compatibility surface, not the primary gateway.

## PR-Driven Delivery Model

Every gateway integration should produce two artifacts:

- ACO artifact: connector, mock fixture, normalized usage records, forecast report, and tests.
- Upstream artifact: PR-ready docs/example/schema/helper that improves the target gateway for all users.

## Later

- Cost anomaly detection.
- Historical forecast accuracy scoring.
- Policy tuning UI for forecast and recommendation rules.
- Automation hooks for scheduled reports, Slack, email, and local notifications.
- Upstream integration PRs for LiteLLM, New API, one-api, and observability tools where maintainers benefit without adopting ACO wholesale.
- Hosted dashboard and database-backed storage after the local workflow is validated.
- Optional integration with Langfuse or Helicone for observability context.
