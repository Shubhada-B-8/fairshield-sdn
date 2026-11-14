from __future__ import annotations


def weighted_max_min(demands: dict[str, float], capacity: float,
                     weights: dict[str, float] | None = None) -> dict[str, float]:
    """Weighted max-min allocation (water filling) with per-flow demand caps.

    The function is deterministic. It allocates no more than each flow's demand
    and no more than the total link capacity.
    """
    if capacity < 0:
        raise ValueError("capacity must be non-negative")
    weights = weights or {}
    result = {key: 0.0 for key in demands}
    active = {key for key, demand in demands.items() if demand > 0}
    remaining = float(capacity)

    for key, value in demands.items():
        if value < 0:
            raise ValueError(f"negative demand for {key}")

    while active and remaining > 1e-12:
        weight_sum = sum(max(float(weights.get(k, 1.0)), 1e-9) for k in active)
        proposed = {
            k: remaining * max(float(weights.get(k, 1.0)), 1e-9) / weight_sum
            for k in active
        }
        saturated = [k for k in active if demands[k] - result[k] <= proposed[k] + 1e-12]
        if not saturated:
            for key in active:
                result[key] += proposed[key]
            remaining = 0.0
            break
        for key in saturated:
            grant = max(0.0, demands[key] - result[key])
            result[key] += grant
            remaining -= grant
            active.remove(key)

    return result


def jains_fairness(values: list[float]) -> float:
    """Jain's fairness index in [0, 1]; empty/all-zero input returns 1."""
    positive = [max(0.0, float(v)) for v in values]
    if not positive or sum(positive) == 0:
        return 1.0
    numerator = sum(positive) ** 2
    denominator = len(positive) * sum(v * v for v in positive)
    return numerator / denominator if denominator else 1.0
