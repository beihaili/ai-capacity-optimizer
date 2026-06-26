# Upstream PR Strategy

ACO should be built so its gateway work can produce useful PRs for mature projects such as LiteLLM, New API, one-api, Langfuse, and Helicone.

## Goal

ACO remains the forecasting and optimization layer. Gateway projects remain the execution layer.

The ideal loop:

1. Build a connector in ACO against public exports or mock data.
2. Discover missing upstream affordances such as docs, schemas, export examples, or optional hooks.
3. Submit small PRs upstream that help all users, not just ACO.
4. Keep ACO's forecasting engine independent so upstream projects do not need to adopt ACO wholesale.

## What Belongs Upstream

Good upstream PR candidates:

- Documentation for exporting spend, quota, budget, or usage data.
- Stable example JSON or CSV export formats.
- Optional API endpoints or CLI commands for usage export.
- Small compatibility helpers for external analytics tools.
- Dashboard links or examples that show how to connect external forecasting tools.

Poor upstream PR candidates:

- Forcing ACO-specific dependencies into another project.
- Large rewrites of gateway routing or billing internals.
- Forecasting logic that maintainers did not ask to own.
- PRs that require real provider credentials to test.

## Target Projects

LiteLLM:

- Strongest first target because it already has spend logs, budgets, keys, model usage, routing, and cost tracking.
- Root repository includes `CONTRIBUTING.md`; use it before opening PRs.
- First likely PR: docs or example showing how to export LiteLLM spend and budget data for forecasting.

New API:

- Good second target for model aggregation and quota distribution use cases.
- License is AGPL-3.0; keep ACO integration boundaries explicit.
- First likely PR: quota and billing export documentation, or a small helper if current exports are insufficient.

one-api:

- Good second target for Chinese relay and channel-management workflows.
- Repository includes `pull_request_template.md`; follow it for PR shape.
- First likely PR: log/quota export documentation and an ACO companion example.

Langfuse and Helicone:

- Useful observability partners, not gateway replacements.
- First likely PRs should be documentation examples showing how traces and usage metadata can enrich ACO forecasts.

## PR Readiness Checklist

Before opening an upstream PR:

- Confirm the feature is useful without requiring ACO.
- Keep the diff small and aligned with the target repo's style.
- Add or update tests when the PR changes behavior.
- Prefer docs/examples for first contact with a project.
- Avoid secrets, provider credentials, and private deployment assumptions.
- Link the ACO use case as context, not as a dependency.
- Open an issue or discussion first if the change touches runtime behavior.

## ACO-Side Requirements

ACO connector work should make upstream PRs easier by producing:

- Mock gateway exports that can be attached to issues or tests.
- Clear normalized usage records.
- Minimal examples that show forecast reports from gateway data.
- Notes about missing upstream fields or confusing export paths.
- Reproducible commands that do not require real API keys.
