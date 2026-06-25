# Contributing

Thanks for helping improve AI Capacity Optimizer.

## Development Setup

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
python -m unittest
```

## Local Smoke Test

```bash
aco init --overwrite
aco mock --days 30 --seed 7
aco report
aco api-complete --prompt "Test unified routing" --debug
```

## Pull Requests

- Keep changes focused.
- Add or update tests for routing, prediction, relay allocation, or API behavior.
- Do not commit real API keys, account data, private usage logs, or customer data.
- Prefer small, readable modules over broad framework rewrites.

