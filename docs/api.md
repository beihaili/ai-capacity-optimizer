# API

Start the local API server:

```bash
aco serve-api --port 8787
```

## Health

```http
GET /health
```

## Capacity

```http
GET /v1/capacity
```

Returns provider pool capacity and the current ACO forecast report.

## Route Debugging

```http
POST /v1/route
Content-Type: application/json

{
  "prompt": "Summarize capacity risk",
  "policy": "balanced"
}
```

## Chat Completions

```http
POST /v1/chat/completions
Content-Type: application/json

{
  "messages": [
    {"role": "user", "content": "Summarize capacity risk"}
  ],
  "policy": "balanced"
}
```

Policies:

- `balanced`: user experience first.
- `quality`: prefer the highest quality pool.
- `cheap`: prefer lower cost pools.
- `fast`: prefer lower latency pools.
- `fill_idle`: prefer pools with more idle capacity.

Policies can be backed by local routing skills in `skills/`. Set `"debug": true` to include routing metadata and see which skill, if any, handled the route.

## Live Relay Mode

ACO can forward chat completions to any OpenAI-compatible API. Configure a provider in `aco/data/provider_pool.json` with:

```json
{
  "provider_id": "personal-relay",
  "provider": "openai_compatible",
  "model": "gpt-4o-mini",
  "enabled": true,
  "base_url": "https://your-relay.example.com/v1",
  "api_key_env": "ACO_RELAY_API_KEY"
}
```

Then run:

```bash
export ACO_RELAY_API_KEY="..."
aco serve-api --live --port 8787
```

In live mode, routing only considers enabled providers that have both `base_url` and `api_key_env`. Successful calls update `usage_log.json` and every attempt is written to `request_log.json`.
