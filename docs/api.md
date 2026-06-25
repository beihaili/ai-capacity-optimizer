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
