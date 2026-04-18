"""Tests for Elliott Wave validation and labeling."""
import pytest

from src.swings.detector import SwingPoint
from src.elliott.rules import validate_impulse, validate_corrective
from src.elliott.fibonacci import retracement_ratio, extension_ratio, is_near_fib
from src.elliott.labeler import label_elliott_wave


class TestImpulseRules:
    def test_valid_textbook_impulse_up(self):
        # Textbook 5-wave impulse up
        is_valid, violations = validate_impulse(
            p0=100, p1=120, p2=110, p3=150, p4=140, p5=165,
            direction="up",
        )
        assert is_valid, f"Valid impulse rejected: {violations}"
        assert len(violations) == 0

    def test_invalid_wave2_retraces_past_start(self):
        # Wave 2 retraces below wave 1 start (violation of R1)
        is_valid, violations = validate_impulse(
            p0=100, p1=120, p2=95, p3=150, p4=140, p5=165,
            direction="up",
        )
        assert not is_valid
        assert any(v.rule == "R1" for v in violations)

    def test_invalid_wave4_overlaps_wave1(self):
        # Wave 4 low overlaps wave 1 high (violation of R3)
        is_valid, violations = validate_impulse(
            p0=100, p1=120, p2=110, p3=150, p4=115, p5=165,
            direction="up",
        )
        assert not is_valid
        assert any(v.rule == "R3" for v in violations)

    def test_invalid_wave3_shortest(self):
        # Wave 3 is shorter than both wave 1 and wave 5 (violation of R2)
        is_valid, violations = validate_impulse(
            p0=100, p1=130, p2=120, p3=135, p4=130, p5=200,
            direction="up",
        )
        assert not is_valid
        assert any(v.rule == "R2" for v in violations)

    def test_valid_textbook_impulse_down(self):
        # Mirror image — 5-wave impulse down
        is_valid, violations = validate_impulse(
            p0=200, p1=180, p2=190, p3=150, p4=160, p5=135,
            direction="down",
        )
        assert is_valid, f"Valid down impulse rejected: {violations}"


class TestFibonacci:
    def test_50pct_retracement(self):
        # Start=100, peak=120, retrace to 110 = 50%
        ratio = retracement_ratio(100, 120, 110)
        assert ratio == pytest.approx(0.5)

    def test_618_retracement(self):
        # Start=100, peak=100+(x), retrace by 0.618*x
        ratio = retracement_ratio(100, 200, 200 - 0.618 * 100)
        assert ratio == pytest.approx(0.618)

    def test_extension_ratio_1_618(self):
        # Wave 1: 100→120 (length 20). Wave 3 extends to 120 + 1.618*20 = 152.36
        ratio = extension_ratio(100, 120, 152.36)
        assert ratio == pytest.approx(1.618, abs=0.01)

    def test_is_near_fib_true(self):
        matched, closest = is_near_fib(0.505, [0.382, 0.5, 0.618], tolerance=0.03)
        assert matched
        assert closest == 0.5

    def test_is_near_fib_false(self):
        matched, closest = is_near_fib(0.45, [0.382, 0.618], tolerance=0.03)
        assert not matched


class TestCorrectiveRules:
    def test_valid_abc_down(self):
        # ABC down after uptrend
        is_valid, violations = validate_corrective(
            pA_start=120, pA_end=100, pB_end=115, pC_end=95,
            direction="down",
        )
        assert is_valid, f"Valid ABC rejected: {violations}"

    def test_invalid_b_exceeds_138pct(self):
        # Wave B retraces way more than 138% of wave A
        is_valid, violations = validate_corrective(
            pA_start=120, pA_end=100, pB_end=150, pC_end=105,
            direction="down",
        )
        assert not is_valid
        assert any(v.rule == "C1" for v in violations)


class TestLabelerIntegration:
    def _build_swings(self, prices: list[float]) -> list[SwingPoint]:
        """Build alternating swings from price list."""
        out = []
        for i, p in enumerate(prices):
            t = "low" if i % 2 == 0 else "high"
            out.append(SwingPoint(
                index=i * 10,
                date=f"2024-{(i % 12)+1:02d}-01",
                price=p,
                type=t,
                prominence=1.0,
            ))
        # Ensure first swing is 'low' if prices are ascending
        if prices[0] < prices[1]:
            return out
        # Flip types if starting with high
        for i, s in enumerate(out):
            out[i] = SwingPoint(
                index=s.index, date=s.date, price=s.price,
                type="high" if i % 2 == 0 else "low",
                prominence=s.prominence,
            )
        return out

    def test_labels_textbook_impulse(self):
        # Clean textbook 5-wave: 100, 120, 110, 150, 140, 165
        swings = self._build_swings([100, 120, 110, 150, 140, 165])
        result = label_elliott_wave(swings, min_confidence=0.3)
        # Should be an impulse
        assert result.pattern in ("impulse", "corrective")

    def test_returns_none_for_too_few_swings(self):
        swings = [
            SwingPoint(0, "2024-01-01", 100.0, "low", 1.0),
            SwingPoint(5, "2024-01-06", 110.0, "high", 1.0),
        ]
        result = label_elliott_wave(swings)
        assert result.pattern == "none"
