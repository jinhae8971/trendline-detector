"""Tests for trendline fitting and scoring."""
import numpy as np
import pandas as pd
import pytest

from src.swings.detector import SwingPoint, detect_swings
from src.trendlines.fitter import fit_trendlines, _line_from_two_points
from src.trendlines.scorer import score_trendline


class TestLineMath:
    def test_line_from_two_points_positive_slope(self):
        p1 = SwingPoint(0, "2024-01-01", 100.0, "low", 1.0)
        p2 = SwingPoint(10, "2024-01-11", 110.0, "low", 1.0)
        slope, intercept = _line_from_two_points(p1, p2)
        assert slope == pytest.approx(1.0)
        assert intercept == pytest.approx(100.0)

    def test_line_from_two_points_negative_slope(self):
        p1 = SwingPoint(0, "2024-01-01", 100.0, "high", 1.0)
        p2 = SwingPoint(20, "2024-01-21", 80.0, "high", 1.0)
        slope, intercept = _line_from_two_points(p1, p2)
        assert slope == pytest.approx(-1.0)
        assert intercept == pytest.approx(100.0)


class TestFitTrendlines:
    def test_uptrend_has_support_line(self):
        # Build a clean uptrend with clear higher lows
        n = 100
        t = np.arange(n)
        trend = 100 + t * 0.5
        oscillation = 3 * np.sin(2 * np.pi * t / 10)
        base = trend + oscillation
        df = pd.DataFrame({
            "open": base,
            "high": base + 0.3,
            "low": base - 0.3,
            "close": base,
        }, index=pd.date_range("2024-01-01", periods=n, freq="D"))

        swings = detect_swings(df, distance=3)
        tls = fit_trendlines(df, swings, min_touches=2, top_k=10)

        # At least one should be a support line (rising)
        support_lines = [t for t in tls if t.type == "support" and t.slope > 0]
        assert len(support_lines) > 0, "Uptrend should produce rising support lines"

    def test_top_k_limit(self):
        # Long random-walk data, many swings = many candidate lines
        np.random.seed(42)
        n = 200
        prices = 100 + np.cumsum(np.random.randn(n))
        df = pd.DataFrame({
            "open": prices,
            "high": prices + 0.5,
            "low": prices - 0.5,
            "close": prices,
        }, index=pd.date_range("2024-01-01", periods=n, freq="D"))

        swings = detect_swings(df, distance=3)
        tls = fit_trendlines(df, swings, min_touches=2, top_k=5)
        assert len(tls) <= 5

    def test_scores_sorted_desc(self):
        n = 100
        t = np.arange(n)
        base = 100 + t * 0.3 + 2 * np.sin(2 * np.pi * t / 12)
        df = pd.DataFrame({
            "open": base, "high": base + 0.3,
            "low": base - 0.3, "close": base,
        }, index=pd.date_range("2024-01-01", periods=n, freq="D"))
        swings = detect_swings(df, distance=3)
        tls = fit_trendlines(df, swings, min_touches=2)
        for i in range(len(tls) - 1):
            assert tls[i].score >= tls[i + 1].score, "Trendlines not sorted by score"


class TestScorer:
    def test_score_is_between_0_and_1(self):
        n = 100
        t = np.arange(n)
        base = 100 + t * 0.2
        df = pd.DataFrame({
            "open": base, "high": base + 0.3,
            "low": base - 0.3, "close": base,
        }, index=pd.date_range("2024-01-01", periods=n, freq="D"))
        swings = detect_swings(df, distance=3)
        tls = fit_trendlines(df, swings, min_touches=2)
        for tl in tls:
            assert 0.0 <= tl.score <= 1.0, f"Score out of range: {tl.score}"
