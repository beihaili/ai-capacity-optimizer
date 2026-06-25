# Skills

ACO skills are local, explicit extensions loaded from the repository `skills/` directory.

The first implementation is intentionally conservative:

- no remote installation
- no automatic third-party code execution
- no package registry access
- no secrets in skill manifests

## Manifest

Each skill has a `skill.json` file:

```json
{
  "name": "route_fill_idle",
  "version": "0.1.0",
  "type": "routing_policy",
  "policy": "fill_idle",
  "description": "Prefer provider pools with the most remaining token capacity.",
  "entrypoint": "handler:run",
  "inputs": ["policy", "estimated_usage", "candidates"],
  "outputs": ["ranked_provider_ids", "reason"],
  "enabled": true
}
```

## Routing Skills

Routing skills receive candidate providers and return a ranked provider id list.

```python
def run(context: dict) -> dict:
    candidates = context["candidates"]
    ranked = sorted(
        candidates,
        key=lambda item: item["provider"]["remaining_tokens"],
        reverse=True,
    )
    return {
        "ranked_provider_ids": [item["provider"]["provider_id"] for item in ranked],
        "reason": "ranked by remaining token capacity",
    }
```

## CLI

```bash
aco skills-list
aco api-complete --prompt "Use idle capacity" --policy fill_idle --debug
```

Set a custom skill directory:

```bash
aco --skills-dir ./skills api-complete --prompt "Use idle capacity" --policy fill_idle --debug
```

