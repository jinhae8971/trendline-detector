"""Elliott Wave labeling — finds the best 5-wave or ABC structure in swings.

Strategy:
    1. Take the most recent 7 swings (6 gives us 5-wave impulse, plus 1 for alt).
    2. Try both "up" and "down" interpretations.
    3. For each valid impulse, score using Fibonacci fit + wave length ratios.
    4. Return the best-scoring labeling with confidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

from ..swings.detector import SwingPoint
from .rules import validate_impulse, validate_corrective
from .fibonacci import retracement_ratio, extension_ratio, is_near_fib


@dataclass
class WaveLabel:
    """A single wave segment labeled (e.g., wave 1, wave 2, ...)."""

    wave: str                 # '1', '2', '3', '4', '5', 'A', 'B', 'C'
    start_index: int
    start_date: str
    start_price: float
    end_index: int
    end_date: str
    end_price: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ElliottWave:
    """Complete Elliott Wave analysis result."""

    pattern: str              # 'impulse' | 'corrective' | 'none'
    direction: str            # 'up' | 'down'
    labels: list[WaveLabel] = field(default_factory=list)
    current_wave: str | None = None  # '1', '2', ..., 'complete', None
    confidence: float = 0.0   # [0, 1]
    violations: list[str] = field(default_factory=list)
    fib_matches: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "pattern": self.pattern,
            "direction": self.direction,
            "labels": [l.to_dict() for l in self.labels],
            "current_wave": self.current_wave,
            "confidence": self.confidence,
            "violations": self.violations,
            "fib_matches": self.fib_matches,
        }


def _score_impulse(
    p0: float, p1: float, p2: float, p3: float, p4: float, p5: float,
    direction: str,
) -> tuple[float, list[dict]]:
    """Compute a Fibonacci-based confidence score for an impulse wave."""
    fib_matches: list[dict] = []
    score_components = []

    # Wave 2 retracement of wave 1 — ideal 0.5 or 0.618
    w2_retrace = retracement_ratio(p0, p1, p2)
    matched, closest = is_near_fib(w2_retrace, [0.382, 0.5, 0.618, 0.786])
    if matched:
        fib_matches.append({
            "wave": "2",
            "ratio_type": "retracement_of_1",
            "actual": round(w2_retrace, 3),
            "fib": closest,
        })
        score_components.append(1.0)
    else:
        score_components.append(0.3)

    # Wave 3 extension of wave 1 — ideal 1.618
    w3_extension = extension_ratio(p0, p1, p3)
    matched, closest = is_near_fib(w3_extension, [1.0, 1.272, 1.618, 2.0, 2.618])
    if matched:
        fib_matches.append({
            "wave": "3",
            "ratio_type": "extension_of_1",
            "actual": round(w3_extension, 3),
            "fib": closest,
        })
        score_components.append(1.0)
    else:
        score_components.append(0.3)

    # Wave 4 retracement of wave 3 — ideal 0.236 or 0.382
    w4_retrace = retracement_ratio(p2, p3, p4)
    matched, closest = is_near_fib(w4_retrace, [0.236, 0.382, 0.5])
    if matched:
        fib_matches.append({
            "wave": "4",
            "ratio_type": "retracement_of_3",
            "actual": round(w4_retrace, 3),
            "fib": closest,
        })
        score_components.append(1.0)
    else:
        score_components.append(0.3)

    # Wave 5 relation to wave 1 — ideal 0.618, 1.0, or 1.618
    if direction == "up":
        w5_len = p5 - p4
        w1_len = p1 - p0
    else:
        w5_len = p4 - p5
        w1_len = p0 - p1
    if w1_len > 0:
        w5_ratio = w5_len / w1_len
        matched, closest = is_near_fib(w5_ratio, [0.618, 1.0, 1.618])
        if matched:
            fib_matches.append({
                "wave": "5",
                "ratio_type": "length_vs_1",
                "actual": round(w5_ratio, 3),
                "fib": closest,
            })
            score_components.append(1.0)
        else:
            score_components.append(0.3)
    else:
        score_components.append(0.3)

    confidence = sum(score_components) / len(score_components)
    return confidence, fib_matches


def _build_labels(
    swings: list[SwingPoint],
    indices: list[int],
    wave_names: list[str],
) -> list[WaveLabel]:
    """Build WaveLabel objects from selected swing indices and names."""
    labels: list[WaveLabel] = []
    for i in range(len(indices) - 1):
        start_swing = swings[indices[i]]
        end_swing = swings[indices[i + 1]]
        labels.append(WaveLabel(
            wave=wave_names[i],
            start_index=start_swing.index,
            start_date=start_swing.date,
            start_price=start_swing.price,
            end_index=end_swing.index,
            end_date=end_swing.date,
            end_price=end_swing.price,
        ))
    return labels


def label_elliott_wave(
    swings: list[SwingPoint],
    *,
    min_confidence: float = 0.5,
) -> ElliottWave:
    """Attempt to label the most recent Elliott Wave structure in swings.

    Needs at least 6 swings to try a 5-wave impulse. If we have 7+ swings,
    we try the most recent 6 first (complete impulse from p0 to p5). If
    the impulse is incomplete (wave 5 still forming), we note that.

    Returns ElliottWave with pattern='none' if no valid structure found.
    """
    n = len(swings)

    if n < 4:
        return ElliottWave(
            pattern="none",
            direction="up",
            violations=[f"Need at least 4 swings, got {n}"],
        )

    best: ElliottWave | None = None

    # Try all complete 5-wave impulses ending at the latest swings
    # We need 6 swings: p0, p1, p2, p3, p4, p5
    if n >= 6:
        # Try the last 6 swings
        last_6 = swings[-6:]
        p_prices = [s.price for s in last_6]
        p_indices = list(range(n - 6, n))

        # Determine direction: if p0 < p1, we're testing "up" direction
        direction = "up" if p_prices[0] < p_prices[1] else "down"

        is_valid, violations = validate_impulse(
            p_prices[0], p_prices[1], p_prices[2],
            p_prices[3], p_prices[4], p_prices[5],
            direction=direction,
        )

        if is_valid:
            confidence, fib_matches = _score_impulse(
                p_prices[0], p_prices[1], p_prices[2],
                p_prices[3], p_prices[4], p_prices[5],
                direction=direction,
            )
            if confidence >= min_confidence:
                labels = _build_labels(
                    swings, p_indices, ["1", "2", "3", "4", "5"],
                )
                best = ElliottWave(
                    pattern="impulse",
                    direction=direction,
                    labels=labels,
                    current_wave="complete",  # 5 waves found
                    confidence=round(confidence, 3),
                    violations=[],
                    fib_matches=fib_matches,
                )

    # If no complete impulse found, try an incomplete one (4 or 5 waves)
    if best is None and n >= 5:
        last_5 = swings[-5:]
        p_prices = [s.price for s in last_5]
        p_indices = list(range(n - 5, n))
        direction = "up" if p_prices[0] < p_prices[1] else "down"

        # Check R1 and R3 on partial (waves 1-4 only)
        p0, p1, p2, p3, p4 = p_prices

        partial_violations: list[str] = []
        if direction == "up":
            if p2 < p0:
                partial_violations.append("Wave 2 retraced below wave 1 start")
            if p4 < p1:
                partial_violations.append("Wave 4 overlapped wave 1 territory")
        else:
            if p2 > p0:
                partial_violations.append("Wave 2 retraced above wave 1 start")
            if p4 > p1:
                partial_violations.append("Wave 4 overlapped wave 1 territory")

        if not partial_violations:
            # Partial scoring on waves 2, 3, 4
            w2_retrace = retracement_ratio(p0, p1, p2)
            w3_extension = extension_ratio(p0, p1, p3)
            w4_retrace = retracement_ratio(p2, p3, p4)

            fib_matches = []
            score_parts = []
            for ratio, targets, label in [
                (w2_retrace, [0.382, 0.5, 0.618, 0.786], "2"),
                (w3_extension, [1.0, 1.272, 1.618, 2.0], "3"),
                (w4_retrace, [0.236, 0.382, 0.5], "4"),
            ]:
                matched, closest = is_near_fib(ratio, targets)
                if matched:
                    fib_matches.append({
                        "wave": label,
                        "actual": round(ratio, 3),
                        "fib": closest,
                    })
                    score_parts.append(1.0)
                else:
                    score_parts.append(0.3)

            confidence = sum(score_parts) / len(score_parts)
            if confidence >= min_confidence:
                labels = _build_labels(
                    swings, p_indices, ["1", "2", "3", "4"],
                )
                best = ElliottWave(
                    pattern="impulse",
                    direction=direction,
                    labels=labels,
                    current_wave="5",  # Wave 5 is in progress
                    confidence=round(confidence, 3),
                    violations=[],
                    fib_matches=fib_matches,
                )

    # If still no impulse, try a corrective ABC
    if best is None and n >= 4:
        last_4 = swings[-4:]
        p_prices = [s.price for s in last_4]
        p_indices = list(range(n - 4, n))
        pA_start, pA_end, pB_end, pC_end = p_prices
        direction = "down" if pA_start > pA_end else "up"

        is_valid, violations = validate_corrective(
            pA_start, pA_end, pB_end, pC_end, direction=direction,
        )
        if is_valid:
            labels = _build_labels(swings, p_indices, ["A", "B", "C"])
            best = ElliottWave(
                pattern="corrective",
                direction=direction,
                labels=labels,
                current_wave="complete",
                confidence=0.6,  # Corrective patterns are less precise
                violations=[],
            )

    if best is None:
        return ElliottWave(
            pattern="none",
            direction="up",
            violations=["No valid Elliott Wave structure found in recent swings"],
        )

    return best
