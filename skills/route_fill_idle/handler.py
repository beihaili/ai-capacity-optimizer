"""Fill-idle routing skill."""


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

