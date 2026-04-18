"""Elliott Wave structural rules.

Impulse (5-wave) rules — MUST be satisfied:
    R1. Wave 2 cannot retrace more than 100% of Wave 1.
        (If wave 2 < wave 1 start, it's invalid.)
    R2. Wave 3 cannot be the shortest of waves 1, 3, 5.
    R3. Wave 4 cannot overlap the price territory of Wave 1.
        (For uptrend: wave 4 low > wave 1 high.
         For downtrend: wave 4 high < wave 1 low.)

Impulse guidelines — preferred but not strict:
    G1. Wave 3 is often the longest and never the shortest.
    G2. Wave 5 is often similar in length to wave 1 (0.618, 1.0, or 1.618x).
    G3. Wave 2 commonly retraces 50-61.8% of wave 1.
    G4. Wave 4 commonly retraces 23.6-38.2% of wave 3.

Corrective (ABC) rules:
    C1. Wave B cannot retrace more than 138% of wave A (otherwise it's not ABC).
    C2. Wave C is often 1.0 or 1.618x of wave A.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RuleViolation:
    """Describes why a wave structure is invalid."""

    rule: str
    reason: str


def validate_impulse(
    p0: float,  # wave 1 start (local low for uptrend)
    p1: float,  # wave 1 end (= wave 2 start)
    p2: float,  # wave 2 end (= wave 3 start)
    p3: float,  # wave 3 end (= wave 4 start)
    p4: float,  # wave 4 end (= wave 5 start)
    p5: float,  # wave 5 end
    direction: str = "up",
) -> tuple[bool, list[RuleViolation]]:
    """Validate a 5-wave impulse structure.

    Args:
        p0..p5: 6 consecutive price points defining waves 1-5.
        direction: 'up' for bullish impulse, 'down' for bearish.

    Returns:
        (is_valid, violations_list)
    """
    violations: list[RuleViolation] = []

    if direction == "up":
        # R1: wave 2 cannot retrace below wave 1 start
        if p2 < p0:
            violations.append(RuleViolation(
                rule="R1",
                reason=f"Wave 2 retraced below wave 1 start ({p2:.2f} < {p0:.2f})",
            ))

        # R3: wave 4 cannot overlap wave 1 territory
        #     In uptrend: p4 (wave 4 end) must stay above p1 (wave 1 end)
        if p4 < p1:
            violations.append(RuleViolation(
                rule="R3",
                reason=f"Wave 4 overlapped wave 1 territory ({p4:.2f} < {p1:.2f})",
            ))

        # R2: wave 3 cannot be the shortest of 1, 3, 5
        wave1_len = p1 - p0
        wave3_len = p3 - p2
        wave5_len = p5 - p4
        if wave3_len < wave1_len and wave3_len < wave5_len:
            violations.append(RuleViolation(
                rule="R2",
                reason=f"Wave 3 is shortest (w1={wave1_len:.2f}, w3={wave3_len:.2f}, w5={wave5_len:.2f})",
            ))

        # Sanity: waves 1, 3, 5 should be "up", waves 2, 4 should be "down"
        if p1 <= p0:
            violations.append(RuleViolation(rule="DIR", reason="Wave 1 not ascending"))
        if p2 >= p1:
            violations.append(RuleViolation(rule="DIR", reason="Wave 2 not descending"))
        if p3 <= p2:
            violations.append(RuleViolation(rule="DIR", reason="Wave 3 not ascending"))
        if p4 >= p3:
            violations.append(RuleViolation(rule="DIR", reason="Wave 4 not descending"))
        if p5 <= p4:
            violations.append(RuleViolation(rule="DIR", reason="Wave 5 not ascending"))

    elif direction == "down":
        # Mirror image of 'up' direction
        if p2 > p0:
            violations.append(RuleViolation(
                rule="R1",
                reason=f"Wave 2 retraced above wave 1 start ({p2:.2f} > {p0:.2f})",
            ))

        if p4 > p1:
            violations.append(RuleViolation(
                rule="R3",
                reason=f"Wave 4 overlapped wave 1 territory ({p4:.2f} > {p1:.2f})",
            ))

        wave1_len = p0 - p1
        wave3_len = p2 - p3
        wave5_len = p4 - p5
        if wave3_len < wave1_len and wave3_len < wave5_len:
            violations.append(RuleViolation(
                rule="R2",
                reason=f"Wave 3 is shortest (w1={wave1_len:.2f}, w3={wave3_len:.2f}, w5={wave5_len:.2f})",
            ))

        # Directions for downward impulse
        if p1 >= p0:
            violations.append(RuleViolation(rule="DIR", reason="Wave 1 not descending"))
        if p2 <= p1:
            violations.append(RuleViolation(rule="DIR", reason="Wave 2 not ascending"))
        if p3 >= p2:
            violations.append(RuleViolation(rule="DIR", reason="Wave 3 not descending"))
        if p4 <= p3:
            violations.append(RuleViolation(rule="DIR", reason="Wave 4 not ascending"))
        if p5 >= p4:
            violations.append(RuleViolation(rule="DIR", reason="Wave 5 not descending"))
    else:
        raise ValueError(f"direction must be 'up' or 'down', got {direction!r}")

    return len(violations) == 0, violations


def validate_corrective(
    pA_start: float,
    pA_end: float,
    pB_end: float,
    pC_end: float,
    direction: str = "down",
) -> tuple[bool, list[RuleViolation]]:
    """Validate a 3-wave corrective (ABC) structure.

    Args:
        pA_start: start of wave A
        pA_end: end of wave A (= start of B)
        pB_end: end of wave B (= start of C)
        pC_end: end of wave C
        direction: 'down' for corrective after uptrend, 'up' for corrective after downtrend.

    Returns:
        (is_valid, violations_list)
    """
    violations: list[RuleViolation] = []

    if direction == "down":
        # C1: wave B cannot retrace > 138% of wave A
        if pA_start == pA_end:
            violations.append(RuleViolation(rule="C1", reason="Wave A has zero length"))
            return False, violations
        wave_a_length = abs(pA_start - pA_end)
        wave_b_retrace = abs(pB_end - pA_end)
        if wave_b_retrace > wave_a_length * 1.38:
            violations.append(RuleViolation(
                rule="C1",
                reason=f"Wave B retraced > 138% of wave A ({wave_b_retrace/wave_a_length:.2%})",
            ))
        # Direction checks for ABC down
        if pA_end >= pA_start:
            violations.append(RuleViolation(rule="DIR", reason="Wave A not descending"))
        if pB_end <= pA_end:
            violations.append(RuleViolation(rule="DIR", reason="Wave B not ascending"))
        if pC_end >= pB_end:
            violations.append(RuleViolation(rule="DIR", reason="Wave C not descending"))

    elif direction == "up":
        if pA_start == pA_end:
            violations.append(RuleViolation(rule="C1", reason="Wave A has zero length"))
            return False, violations
        wave_a_length = abs(pA_end - pA_start)
        wave_b_retrace = abs(pA_end - pB_end)
        if wave_b_retrace > wave_a_length * 1.38:
            violations.append(RuleViolation(
                rule="C1",
                reason=f"Wave B retraced > 138% of wave A ({wave_b_retrace/wave_a_length:.2%})",
            ))
        # Direction checks for ABC up (correction after downtrend)
        if pA_end <= pA_start:
            violations.append(RuleViolation(rule="DIR", reason="Wave A not ascending"))
        if pB_end >= pA_end:
            violations.append(RuleViolation(rule="DIR", reason="Wave B not descending"))
        if pC_end <= pB_end:
            violations.append(RuleViolation(rule="DIR", reason="Wave C not ascending"))
    else:
        raise ValueError(f"direction must be 'up' or 'down', got {direction!r}")

    return len(violations) == 0, violations
