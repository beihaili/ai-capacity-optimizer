# ACO Goal Loops

## Loop 0: Initialization

Goal: Build AI Capacity Optimizer MVP foundations.

Tasks:

1. Create `usage_log.json` schema support.
2. Create `quota_config.json`.
3. Implement usage logging.
4. Generate 30 days of mock usage data.

Verify:

```bash
python -m aco.main init
python -m aco.main mock --days 30
```

## Loop 1: Prediction Engine

Goal: Forecast month-end usage.

Tasks:

1. Implement exponential moving average.
2. Implement linear trend estimator.
3. Implement month-end usage projection.
4. Emit a prediction report as JSON.

Verify:

```bash
python -m aco.main report
```

## Loop 2: Idle Detection

Goal: Detect idle quota and usage risk.

Tasks:

1. Implement idle quota levels.
2. Define green, yellow, and red risk levels.
3. Include an idle risk report.

Verify:

```bash
python -m aco.main report
```

## Loop 3: Optimization Suggestions

Goal: Generate actionable optimization suggestions.

Tasks:

1. Implement rule-based suggestions.
2. Generate actions from idle and usage risk.
3. Simulate task fill with available idle tokens.

Verify:

```bash
python -m aco.main report
```

## Loop 4: Dashboard

Goal: Show quota, forecast, idle risk, and suggestions in a UI.

Tasks:

1. Show current usage rate.
2. Show daily usage trend.
3. Show idle and quota risk.
4. Show optimization suggestions.

Verify:

```bash
streamlit run aco/frontend/dashboard.py
```

## Loop 5: Marketplace Simulation

Goal: Simulate internal capacity matching.

Tasks:

1. Convert idle quota to virtual credits.
2. Match mock internal tasks against idle capacity.
3. Estimate a simple demand/supply index.

Verify:

```bash
python -m aco.main report
```

## Loop 6: Relay Hub

Goal: Add the internal middle station.

Tasks:

1. Create `relay_requests.json`.
2. Implement request validation and persistence.
3. Rank active requests by priority and deadline.
4. Allocate idle tokens to requests with full or partial outcomes.
5. Include relay allocation in the CLI report and dashboard.

Verify:

```bash
python -m aco.main relay-plan
python -m aco.main report
```

## Loop 7: Unified API Gateway

Goal: Collapse multiple providers into one user-facing API.

Tasks:

1. Create `provider_pool.json`.
2. Implement provider scoring by quality, remaining capacity, cost, and latency.
3. Add OpenAI-compatible-ish chat completion simulation.
4. Add local HTTP endpoints for health, capacity, routing, and completions.
5. Add CLI commands for routing, provider listing, and serving the API.

Verify:

```bash
python -m aco.main provider-list
python -m aco.main api-complete --prompt "Test routing" --debug
python -m aco.main serve-api --port 8787
```
