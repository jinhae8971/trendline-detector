"""Fibonacci ratios for Elliott Wave validation."""
from __future__ import annotations


# Standard Fibonacci retracement levels (for corrective waves)
FIB_RETRACEMENT = [0.236, 0.382, 0.5, 0.618, 0.786]

# Standard Fibonacci extension levels (for impulse wave 3 and 5)
FIB_EXTENSION = [1.0, 1.272, 1.382, 1.618, 2.0, 2.618]

# All standard Fibonacci ratios we test against
FIB_RATIOS = FIB_RETRACEMENT + FIB_EXTENSION


def retracement_ratio(start_price: float, peak_price: float, retrace_price: float) -> float:
    """How much of the (start→peak) move was retraced?

    Returns a value in [0, ∞]. 0.5 = 50% retracement, 1.0 = full retracement.
    """
    move = peak_price - start_price
    if abs(move) < 1e-9:
        return 0.0
    return (peak_price - retrace_price) / move


def extension_ratio(wave1_start: float, wave1_end: float, wave3_end: float) -> float:
    """Length of wave 3 relative to wave 1.

    wave3_length / wave1_length. For impulse waves, wave 3 often extends
    to 1.618x or 2.618x of wave 1.
    """
    wave1_length = abs(wave1_end - wave1_start)
    wave3_length = abs(wave3_end - wave1_end)
    if wave1_length < 1e-9:
        return 0.0
    return wave3_length / wave1_length


def is_near_fib(
    actual_ratio: float,
    target_fibs: list[float] | None = None,
    tolerance: float = 0.05,
) -> tuple[bool, float | None]:
    """Check if a ratio is near any standard Fibonacci level.

    Args:
        actual_ratio: The computed ratio to test.
        target_fibs: List of Fibonacci targets. Defaults to FIB_RATIOS.
        tolerance: Absolute tolerance (0.05 = ±0.05).

    Returns:
        (matched: bool, closest_fib: float or None)
    """
    if target_fibs is None:
        target_fibs = FIB_RATIOS
    closest = min(target_fibs, key=lambda f: abs(f - actual_ratio))
    matched = abs(closest - actual_ratio) <= tolerance
    return matched, closest if matched else None
