"""Low-cost routing skill."""


def run(context: dict) -> dict:
    candidates = context["candidates"]
    ranked = sorted(
        candidates,
        key=lambda item: (
            item["provider"]["cost_per_1k_tokens"],
            -item["provider"]["quality_score"],
        ),
    )
    return {
        "ranked_provider_ids": [item["provider"]["provider_id"] for item in ranked],
        "reason": "ranked by cost, then quality",
    }

