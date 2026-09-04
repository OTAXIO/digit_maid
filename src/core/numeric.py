"""Small helpers for keeping UI-facing numeric values finite and bounded."""

from __future__ import annotations

import math
from typing import Any


def bounded_float(
    value: Any,
    *,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    """Return a finite float clamped to the supplied inclusive range."""

    if not math.isfinite(minimum) or not math.isfinite(maximum) or minimum > maximum:
        raise ValueError("invalid numeric bounds")

    try:
        fallback = float(default)
    except (TypeError, ValueError, OverflowError):
        fallback = minimum
    if not math.isfinite(fallback):
        fallback = minimum
    fallback = max(minimum, min(maximum, fallback))

    if isinstance(value, bool):
        return fallback
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return fallback
    if not math.isfinite(number):
        return fallback
    return max(minimum, min(maximum, number))


def bounded_int(
    value: Any,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    """Return an integer clamped to the supplied inclusive range."""

    if minimum > maximum:
        raise ValueError("invalid numeric bounds")
    fallback = max(minimum, min(maximum, int(default)))
    if isinstance(value, bool):
        return fallback
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError):
        return fallback
    return max(minimum, min(maximum, number))
