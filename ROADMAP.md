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

## Next

- LiteLLM connector first: import spend logs, budgets, keys, model usage, and daily usage history.
- New API and one-api connectors next: import quota, user/channel usage, and billing logs.
- Normalize all gateway imports into ACO usage records.
- Generate month-end usage, idle-capacity, and overrun forecasts from imported gateway data.
- Produce optimization recommendations for batch jobs, summaries, code reviews, and eval workloads.
- Keep the local OpenAI-compatible API as a demo and fallback compatibility surface, not the primary gateway.

## Later

- Cost anomaly detection.
- Historical forecast accuracy scoring.
- Policy tuning UI for forecast and recommendation rules.
- Automation hooks for scheduled reports, Slack, email, and local notifications.
- Hosted dashboard and database-backed storage after the local workflow is validated.
- Optional integration with Langfuse or Helicone for observability context.
