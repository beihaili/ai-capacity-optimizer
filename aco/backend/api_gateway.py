"""Unified API routing over multiple AI capacity pools."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import time
from pathlib import Path
from uuid import uuid4

from aco.backend.quota_model import load_quota_config


POLICY_WEIGHTS = {
    "balanced": {"quality": 0.55, "capacity": 0.25, "cost": 0.10, "latency": 0.10},
    "quality": {"quality": 0.60, "capacity": 0.20, "cost": 0.10, "latency": 0.10},
    "cheap": {"quality": 0.20, "capacity": 0.25, "cost": 0.45, "latency": 0.10},
    "fast": {"quality": 0.25, "capacity": 0.20, "cost": 0.10, "latency": 0.45},
    "fill_idle": {"quality": 0.25, "capacity": 0.55, "cost": 0.10, "latency": 0.10},
}


@dataclass(frozen=True)
class ProviderConfig:
    provider_id: str
    provider: str
    model: str
    monthly_budget_tokens: int
    current_usage: int
    quality_score: float
    latency_ms: int
    cost_per_1k_tokens: float
    enabled: bool = True
    capabilities: list[str] = field(default_factory=list)

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.monthly_budget_tokens - self.current_usage)

    @classmethod
    def from_dict(cls, data: dict) -> "ProviderConfig":
        provider = cls(
            provider_id=str(data["provider_id"]),
            provider=str(data["provider"]),
            model=str(data["model"]),
            monthly_budget_tokens=int(data["monthly_budget_tokens"]),
            current_usage=int(data.get("current_usage", 0)),
            quality_score=float(data.get("quality_score", 0.75)),
            latency_ms=int(data.get("latency_ms", 1_000)),
            cost_per_1k_tokens=float(data.get("cost_per_1k_tokens", 0.01)),
            enabled=bool(data.get("enabled", True)),
            capabilities=[str(item) for item in data.get("capabilities", [])],
        )
        provider.validate()
        return provider

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["remaining_tokens"] = self.remaining_tokens
        return payload

    def with_current_usage(self, current_usage: int) -> "ProviderConfig":
        return ProviderConfig(
            provider_id=self.provider_id,
            provider=self.provider,
            model=self.model,
            monthly_budget_tokens=self.monthly_budget_tokens,
            current_usage=max(0, int(current_usage)),
            quality_score=self.quality_score,
            latency_ms=self.latency_ms,
            cost_per_1k_tokens=self.cost_per_1k_tokens,
            enabled=self.enabled,
            capabilities=list(self.capabilities),
        )

    def validate(self) -> None:
        if not self.provider_id:
            raise ValueError("provider_id is required")
        if not self.provider:
            raise ValueError("provider is required")
        if not self.model:
            raise ValueError("model is required")
        if self.monthly_budget_tokens <= 0:
            raise ValueError("monthly_budget_tokens must be positive")
        if self.current_usage < 0:
            raise ValueError("current_usage must be non-negative")
        if not 0 <= self.quality_score <= 1:
            raise ValueError("quality_score must be between 0 and 1")
        if self.latency_ms <= 0:
            raise ValueError("latency_ms must be positive")
        if self.cost_per_1k_tokens < 0:
            raise ValueError("cost_per_1k_tokens must be non-negative")


def default_provider_pool() -> list[ProviderConfig]:
    return [
        ProviderConfig(
            provider_id="chatgpt-pro-main",
            provider="openai",
            model="gpt-4o",
            monthly_budget_tokens=1_000_000,
            current_usage=0,
            quality_score=0.96,
            latency_ms=900,
            cost_per_1k_tokens=0.012,
            capabilities=["chat", "code", "reasoning"],
        ),
        ProviderConfig(
            provider_id="claude-team-relay",
            provider="anthropic",
            model="claude-3-5-sonnet",
            monthly_budget_tokens=600_000,
            current_usage=210_000,
            quality_score=0.94,
            latency_ms=1_100,
            cost_per_1k_tokens=0.011,
            capabilities=["chat", "writing", "analysis"],
        ),
        ProviderConfig(
            provider_id="cheap-batch-pool",
            provider="openrouter",
            model="gpt-4o-mini",
            monthly_budget_tokens=2_000_000,
            current_usage=900_000,
            quality_score=0.76,
            latency_ms=650,
            cost_per_1k_tokens=0.002,
            capabilities=["chat", "batch", "summary"],
        ),
    ]


def load_provider_pool(path: str | Path, *, quota_path: str | Path | None = None) -> list[ProviderConfig]:
    provider_path = Path(path)
    if not provider_path.exists():
        return default_provider_pool()
    raw = json.loads(provider_path.read_text(encoding="utf-8"))
    raw_providers = raw["providers"] if isinstance(raw, dict) and "providers" in raw else raw
    providers = [ProviderConfig.from_dict(item) for item in raw_providers]
    if quota_path is not None and Path(quota_path).exists():
        quota = load_quota_config(quota_path)
        providers = [
            provider.with_current_usage(quota.current_usage)
            if provider.provider_id == "chatgpt-pro-main"
            else provider
            for provider in providers
        ]
    return providers


def save_provider_pool(path: str | Path, providers: list[ProviderConfig]) -> None:
    provider_path = Path(path)
    provider_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"providers": [provider.to_dict() for provider in providers]}
    provider_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def seed_provider_pool(*, data_dir: str | Path, overwrite: bool = False) -> dict:
    data_path = Path(data_dir)
    provider_path = data_path / "provider_pool.json"
    if provider_path.exists() and not overwrite:
        providers = load_provider_pool(provider_path, quota_path=data_path / "quota_config.json")
        return {"created": False, "providers": len(providers), "provider_pool": str(provider_path)}
    providers = default_provider_pool()
    save_provider_pool(provider_path, providers)
    return {"created": True, "providers": len(providers), "provider_pool": str(provider_path)}


def estimate_request_tokens(payload: dict) -> dict:
    if "estimated_tokens" in payload:
        total = max(1, int(payload["estimated_tokens"]))
        return {"prompt_tokens": max(1, total // 2), "completion_tokens": total - max(1, total // 2), "total_tokens": total}

    if "messages" in payload:
        text = " ".join(str(message.get("content", "")) for message in payload["messages"])
    else:
        text = str(payload.get("prompt", ""))

    prompt_tokens = max(1, len(text) // 4)
    completion_tokens = max(1, int(payload.get("max_tokens", 256)))
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }


def normalize_policy(policy: str | None) -> str:
    if not policy:
        return "balanced"
    return policy if policy in POLICY_WEIGHTS else "balanced"


def score_candidates(providers: list[ProviderConfig], *, estimated_tokens: int, policy: str) -> list[dict]:
    enabled = [
        provider
        for provider in providers
        if provider.enabled and provider.remaining_tokens >= estimated_tokens
    ]
    if not enabled:
        return []

    max_cost = max(provider.cost_per_1k_tokens for provider in enabled) or 1
    max_latency = max(provider.latency_ms for provider in enabled) or 1
    weights = POLICY_WEIGHTS[normalize_policy(policy)]
    scored = []

    for provider in enabled:
        capacity_score = min(1.0, provider.remaining_tokens / provider.monthly_budget_tokens)
        cost_score = 1 - min(1.0, provider.cost_per_1k_tokens / max_cost)
        latency_score = 1 - min(1.0, provider.latency_ms / max_latency)
        score = (
            weights["quality"] * provider.quality_score
            + weights["capacity"] * capacity_score
            + weights["cost"] * cost_score
            + weights["latency"] * latency_score
        )
        scored.append(
            {
                "provider": provider.to_dict(),
                "score": round(score, 4),
                "score_parts": {
                    "quality": round(provider.quality_score, 4),
                    "capacity": round(capacity_score, 4),
                    "cost": round(cost_score, 4),
                    "latency": round(latency_score, 4),
                },
            }
        )

    return sorted(scored, key=lambda item: item["score"], reverse=True)


def route_unified_request(
    *,
    data_dir: str | Path,
    payload: dict,
) -> dict:
    data_path = Path(data_dir)
    providers = load_provider_pool(data_path / "provider_pool.json", quota_path=data_path / "quota_config.json")
    usage = estimate_request_tokens(payload)
    policy = normalize_policy(str(payload.get("aco_policy") or payload.get("policy") or "balanced"))
    candidates = score_candidates(providers, estimated_tokens=usage["total_tokens"], policy=policy)

    if not candidates:
        return {
            "request_id": f"aco-route-{uuid4().hex[:12]}",
            "policy": policy,
            "estimated_usage": usage,
            "selected": None,
            "fallbacks": [],
            "status": "rejected",
            "reason": "no provider has enough remaining capacity",
        }

    selected = candidates[0]
    return {
        "request_id": f"aco-route-{uuid4().hex[:12]}",
        "policy": policy,
        "estimated_usage": usage,
        "selected": selected,
        "fallbacks": candidates[1:],
        "status": "routed",
        "reason": "highest policy score among eligible providers",
    }


def simulate_chat_completion(*, data_dir: str | Path, payload: dict) -> dict:
    route = route_unified_request(data_dir=data_dir, payload=payload)
    if route["status"] != "routed":
        return {
            "error": {
                "message": route["reason"],
                "type": "aco_capacity_error",
                "code": "no_capacity",
            },
            "aco": route,
        }

    selected_provider = route["selected"]["provider"]
    user_text = extract_user_text(payload)
    content = build_simulated_answer(user_text, selected_provider, expose_route=bool(payload.get("debug", False)))
    response = {
        "id": f"aco-chatcmpl-{uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": selected_provider["model"],
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": route["estimated_usage"],
    }
    if payload.get("debug", False):
        response["aco"] = route
    return response


def extract_user_text(payload: dict) -> str:
    if "messages" in payload:
        for message in reversed(payload["messages"]):
            if message.get("role") == "user":
                return str(message.get("content", ""))
    return str(payload.get("prompt", ""))


def build_simulated_answer(user_text: str, provider: dict, *, expose_route: bool = False) -> str:
    compact = " ".join(user_text.split())
    if len(compact) > 140:
        compact = compact[:137] + "..."
    if not expose_route:
        return f"Simulated unified API response for: {compact or 'empty prompt'}"
    return (
        "ACO unified API routed this request through "
        f"{provider['provider']} / {provider['model']}. "
        f"Simulated response for: {compact or 'empty prompt'}"
    )


def provider_pool_summary(*, data_dir: str | Path) -> dict:
    data_path = Path(data_dir)
    providers = load_provider_pool(data_path / "provider_pool.json", quota_path=data_path / "quota_config.json")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "providers": [provider.to_dict() for provider in providers],
        "total_remaining_tokens": sum(provider.remaining_tokens for provider in providers if provider.enabled),
    }
