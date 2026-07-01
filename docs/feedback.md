# Feedback

ACO is looking for feedback from people who operate LLM gateways, relays, or shared API budgets.

The project is not trying to replace LiteLLM, New API, one-api, Langfuse, or Helicone. ACO is a local forecasting layer that imports usage data from those systems, predicts month-end idle or overrun risk, and recommends useful work for capacity that would otherwise expire.

## What To Try

Run the LiteLLM dashboard export demo:

```bash
python -m pip install -e ".[dev]"
aco init --overwrite --monthly-budget-tokens 100000 --billing-cycle-start 2026-06-01
aco import-litellm --spend-log examples/litellm_dashboard_daily_with_models_export.json
aco report --reference-date 2026-06-26
```

You should see imported usage, detected export shape, a month-end forecast, idle tokens, risk levels, optimization suggestions, and relay allocation.

No real provider key, gateway server, customer data, or private usage log is required.

## Feedback Questions

1. Do you currently run LiteLLM, New API, one-api, OpenRouter, or another LLM gateway?
2. Can you currently predict whether your monthly AI quota or budget will be wasted or exceeded?
3. Would ACO's LiteLLM import plus forecast report be useful in your workflow?
4. Which breakdown matters most: per-model, per-key, per-team, or per-user?
5. What work would you use idle capacity for: summaries, code review, evals, document cleanup, research, or something else?
6. What is missing that would stop you from trying ACO against your own exported data?

## Good Feedback

Useful feedback includes:

- the gateway or relay you use
- the export format you can access
- which fields are missing from ACO's current report
- whether forecasts should be token-based, spend-based, or both
- privacy constraints that affect what ACO can store locally

Please avoid sharing real API keys, private prompts, customer data, or raw production logs.

## Where To Send It

Use GitHub issues:

- Feedback: report whether the current import and forecast flow makes sense.
- Connector request: ask for New API, one-api, Langfuse, Helicone, or another source.
- Upstream PR candidate: propose a docs, export, schema, or helper change that would benefit a gateway project.
