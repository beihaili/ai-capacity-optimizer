# Gateway Integration Roadmap

ACO should become the forecasting and optimization layer above existing LLM gateways, not another generic gateway.

## Layer Model

Execution Layer:

- [LiteLLM](https://github.com/BerriAI/litellm): OpenAI-compatible proxy, provider routing, budgets, spend logs, and load balancing.
- [New API](https://github.com/QuantumNous/new-api): model aggregation, quota, key distribution, and relay management.
- [one-api](https://github.com/songquanpeng/one-api): API management, channel routing, user quota, and Chinese relay scenarios.

Prediction Layer:

- ACO imports gateway usage and quota data.
- ACO predicts month-end usage, idle capacity, waste risk, and overrun risk.
- ACO generates optimization recommendations and task-fill plans.

Observability Layer:

- [Langfuse](https://github.com/langfuse/langfuse) and [Helicone](https://github.com/Helicone/helicone) provide traces, analytics, prompt metadata, and operational context.

## Phase 1: LiteLLM Connector

Goal: turn LiteLLM spend, budget, key, and model usage data into ACO usage history.

Inputs:

- LiteLLM spend logs.
- Budget records.
- Key or team usage.
- Model-level usage.

Outputs:

- Normalized ACO usage records.
- Daily usage history.
- Month-end forecast report.

Acceptance:

- ACO can generate a quota forecast from LiteLLM-derived data without any provider API key.
- Connector tests can run against mock LiteLLM exports.

## Phase 2: New API and one-api Connectors

Goal: support relay systems commonly used for model aggregation and quota distribution.

Inputs:

- Quota records.
- User and channel usage.
- Billing or request logs.

Outputs:

- Normalized ACO usage records.
- Per-user, per-channel, and per-model summaries where source data supports them.
- Shared forecast reports using the same engine as the LiteLLM connector.

Acceptance:

- The same forecast engine works with mock New API and one-api data.
- Connector parsing does not require real credentials.

## Phase 3: Idle Capacity Forecasting

Goal: explain whether capacity will be wasted, exhausted, or paced correctly by the end of the cycle.

Outputs:

- Predicted month-end usage.
- Estimated remaining quota.
- Estimated idle or overrun amount.
- Risk level: green, yellow, or red.

Acceptance:

- Reports clearly answer: expected usage, expected waste, expected overrun risk, and recommended amount to consume or save.

## Phase 4: Optimization Recommendations

Goal: convert idle capacity into useful work suggestions without automatically spending quota.

Recommendation types:

- Batch summarization.
- Documentation or note cleanup.
- Code review and static analysis.
- Evaluation workloads.
- Backlog research tasks.

Acceptance:

- Each recommendation includes reason, estimated token usage, priority, and expected effect on idle capacity.
- Users can inspect and approve recommendations before any automation runs.

## Phase 5: Automation Hooks

Goal: deliver recurring forecast and optimization updates.

Integrations:

- CLI report generation.
- Webhook output for existing gateway dashboards.
- Slack, email, or local notification summaries.
- Optional scheduled runs.

Acceptance:

- Users can receive a daily forecast report.
- Reports can be generated without storing provider secrets in ACO.
