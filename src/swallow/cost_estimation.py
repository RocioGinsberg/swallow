from __future__ import annotations

MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude": (3.0, 15.0),
    "codex": (0.0, 0.0),
    "local": (0.0, 0.0),
    "mock": (0.0, 0.0),
    "mock-remote": (0.0, 0.0),
}


def estimate_tokens(text: str) -> int:
    normalized = (text or "").strip()
    if not normalized:
        return 0
    return max(1, len(normalized) // 4)


def _pricing_for(model_hint: str) -> tuple[float, float]:
    normalized_hint = (model_hint or "").strip().lower()
    if not normalized_hint:
        return (0.0, 0.0)
    for key, pricing in MODEL_PRICING.items():
        if key in normalized_hint:
            return pricing
    return (0.0, 0.0)


def estimate_cost(model_hint: str, input_tokens: int, output_tokens: int) -> float:
    input_price_per_mtok, output_price_per_mtok = _pricing_for(model_hint)
    safe_input_tokens = max(int(input_tokens or 0), 0)
    safe_output_tokens = max(int(output_tokens or 0), 0)
    estimated = (
        (safe_input_tokens / 1_000_000) * input_price_per_mtok
        + (safe_output_tokens / 1_000_000) * output_price_per_mtok
    )
    return round(estimated, 6)
