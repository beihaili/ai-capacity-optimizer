# LiteLLM Phase 0 Upstream Discovery

Last checked: 2026-06-26.

This packet turns the LiteLLM connector work into a PR-driven milestone. The first ACO deliverable should be a local connector against LiteLLM exports. The first LiteLLM deliverable should be a small docs or example PR that helps LiteLLM users export spend and budget data for forecasting without adding ACO as a dependency.

## Target Repository

- Repository: [BerriAI/litellm](https://github.com/BerriAI/litellm)
- Default branch observed through GitHub API: `litellm_internal_staging`
- Contribution guide: [CONTRIBUTING.md](https://github.com/BerriAI/litellm/blob/litellm_internal_staging/CONTRIBUTING.md)
- Agent guidelines: [AGENTS.md](https://github.com/BerriAI/litellm/blob/litellm_internal_staging/AGENTS.md) points contributors to [CLAUDE.md](https://github.com/BerriAI/litellm/blob/litellm_internal_staging/CLAUDE.md)
- License field from GitHub API: `NOASSERTION`; re-check repository metadata before redistributing copied code

## Contribution Rules To Follow

- Sign the LiteLLM CLA before opening a PR.
- Base work on `litellm_internal_staging`, not `main`.
- Keep the PR scoped to one specific problem.
- Use conventional commit and PR title style.
- Backend proxy behavior changes require meaningful mocked tests.
- Unit tests should live under `tests/test_litellm/` and should not make real provider calls.
- Run the target repo's expected checks before submission, especially `make test-unit` and `make lint` when code changes.
- First contact should prefer docs or examples over runtime behavior.

Public PR text in LiteLLM should also follow the repository's style guidance from `CLAUDE.md`: no emojis, no em dashes, no customer names, and keep the description concise.

## LiteLLM Data Surfaces

These surfaces are enough for an ACO Phase 1 connector without asking LiteLLM maintainers for new runtime behavior.

### Spend Logs

Relevant model: `litellm/models/spend_logs.py`

Useful fields:

- `request_id`
- `api_key`
- `model`
- `api_base`
- `call_type`
- `spend`
- `total_tokens`
- `prompt_tokens`
- `completion_tokens`
- `startTime`
- `endTime`
- `user`
- `metadata`
- `cache_hit`
- `cache_key`
- `request_tags`
- `requester_ip_address`

ACO normalization:

| LiteLLM field | ACO field |
| --- | --- |
| `startTime` or `endTime` | `timestamp` |
| `model` | `model` |
| `prompt_tokens` | `tokens_in` |
| `completion_tokens` | `tokens_out` |
| `spend` | `cost_estimate` |
| `call_type` | `session_type` |
| `api_key`, `user`, `metadata`, `request_tags` | optional metadata |

### Budget Data

Relevant model: `litellm/models/budget.py`

Useful fields:

- `budget_id`
- `soft_budget`
- `max_budget`
- `max_parallel_requests`
- `tpm_limit`
- `rpm_limit`
- `model_max_budget`
- `budget_duration`
- `allowed_models`
- `budget_reset_at`
- `created_at`

ACO normalization:

- `max_budget` and `soft_budget` define spend limits.
- `budget_duration`, `budget_reset_at`, and `created_at` define the forecast cycle.
- `model_max_budget` can become model-level capacity constraints.
- `tpm_limit` and `rpm_limit` can become pacing constraints later, but should not block the first connector.

### Spend And Usage Endpoints

Relevant file: `litellm/proxy/spend_tracking/spend_management_endpoints.py`

Observed endpoint families include:

- `/spend/keys`
- `/spend/users`
- `/spend/tags`
- `/global/activity`
- `/global/activity/model`
- `/global/spend/report`
- `/global/spend/logs`
- `/global/spend`
- `/global/spend/keys`
- `/global/spend/teams`
- `/global/spend/models`
- `/provider/budgets`
- `/spend/logs/session/ui`

Connector implication: the first ACO connector should accept exported JSON or CSV fixtures rather than requiring live proxy credentials. Runtime API ingestion can come later after the fixture path is stable.

### Dashboard Export Shape

Relevant files:

- `ui/litellm-dashboard/src/components/EntityUsageExport/types.ts`
- `ui/litellm-dashboard/src/components/EntityUsageExport/utils.ts`

Observed export concepts:

- Export format: `csv` or `json`
- Export scope: `daily`, `daily_with_keys`, or `daily_with_models`
- Entity type: `tag`, `team`, `organization`, `customer`, `agent`, or `user`
- Summary metrics: `total_spend`, `total_api_requests`, `total_successful_requests`, `total_failed_requests`, `total_tokens`
- Breakdown metrics: `spend`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `api_requests`, `successful_requests`, `failed_requests`, `cache_read_input_tokens`, `cache_creation_input_tokens`

Connector implication: ACO should support daily export files first, then add key and model breakdown support.

## ACO Connector Design Note

The first LiteLLM connector should be file-first:

1. Read a mock LiteLLM spend log export.
2. Read optional budget context.
3. Normalize records into ACO usage records.
4. Generate the existing ACO month-end forecast report.
5. Run without a real LiteLLM server, provider key, database, or private spend data.

Initial command shape:

```bash
aco import-litellm \
  --spend-log examples/litellm_spend_logs.json \
  --budget examples/litellm_budget.json \
  --out aco/data/usage_log.json

aco report
```

This command is implemented as the first file-first LiteLLM connector. The optional budget file is imported as context; ACO does not convert LiteLLM dollar budgets into token quotas without an explicit conversion policy.

## Mock Fixture

The fixture should avoid real keys and private prompts.

```json
[
  {
    "request_id": "req_mock_001",
    "api_key": "sk-mock-redacted",
    "model": "gpt-4o-mini",
    "call_type": "completion",
    "spend": 0.0123,
    "total_tokens": 2800,
    "prompt_tokens": 1800,
    "completion_tokens": 1000,
    "startTime": "2026-06-24T12:00:00Z",
    "endTime": "2026-06-24T12:00:03Z",
    "user": "user_mock_001",
    "metadata": {
      "team_id": "team_mock_001",
      "source": "fixture"
    },
    "request_tags": ["forecast-demo"]
  }
]
```

Expected normalized ACO record:

```json
{
  "timestamp": "2026-06-24T12:00:00Z",
  "model": "gpt-4o-mini",
  "tokens_in": 1800,
  "tokens_out": 1000,
  "cost_estimate": 0.0123,
  "session_type": "api"
}
```

## Upstream PR Packet

Proposed PR title:

```text
docs(proxy): add spend export forecasting example
```

Maintainer-facing motivation:

LiteLLM already records spend, token, budget, key, team, and model usage data. A small export and forecasting example would help users understand whether current budgets will be exhausted or left unused by the end of a billing cycle, without changing LiteLLM runtime behavior or requiring external credentials.

Likely target files:

- `cookbook/litellm_proxy_server/spend_export_forecasting.md`
- Optional fixture under a LiteLLM examples or cookbook path if maintainers prefer executable examples.

Expected contents:

- A short explanation of which LiteLLM spend and budget fields external forecasting tools need.
- A mock spend-log JSON payload with redacted keys.
- A CSV or JSON export example based on dashboard usage metrics.
- A note that forecasting can run outside LiteLLM and should not require provider API keys.

Acceptance criteria:

- The example is useful to LiteLLM users even if they never install ACO.
- No real API keys, prompts, customer names, or private deployment details are included.
- No runtime behavior is changed.
- If a script is added, it uses mocked data and has a narrow test or clear manual verification path.

Issue-first decision:

- Docs/example PR: can be prepared directly.
- New endpoint, schema guarantee, CLI export, or runtime behavior PR: open an issue or discussion first and ask maintainers whether they want the surface.

## Next ACO Tasks

1. Extend LiteLLM import support from raw spend logs to dashboard daily export shapes.
2. Add optional model, key, and team summaries from imported LiteLLM fields.
3. Generate a saved forecast report from the mock fixture.
4. Prepare the LiteLLM docs/example PR draft using the fixture and command output.
