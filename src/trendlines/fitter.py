"""Trendline fitting from swing points.

Strategy:
    1. Generate candidate trendlines from all swing pairs (C(n, 2) pairs).
    2. Filter: support lines from lows, resistance lines from highs.
    3. Extend each candidate across the full time range.
    4. Count "touches" — bars where low/high comes within tolerance of line.
    5. Score each candidate (see scorer.py) and return top-K.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from itertools import combinations
from typing import Literal

import numpy as np
import pandas as pd

from ..swings.detector import SwingPoint, _normalize_ohlcv_columns

TrendlineType = Literal["support", "resistance"]


@dataclass
class Trendline:
    """A fitted trendline with its properties."""

    type: TrendlineType       # 'support' (from lows) or 'resistance' (from highs)
    slope: float              # price change per bar (can be negative)
    intercept: float          # y-intercept (price at bar index 0)
    start_index: int          # first swing used to define the line
    end_index: int            # last swing used to define the line
    start_date: str           # ISO date of start
    end_date: str             # ISO date of end
    touch_count: int = 0      # how many bars came within tolerance
    touch_indices: list[int] = field(default_factory=list)
    score: float = 0.0        # overall quality score [0, 1]

    def price_at(self, bar_index: int) -> float:
        """Return the trendline price at a given bar index."""
        return self.slope * bar_index + self.intercept

    def to_dict(self) -> dict:
        return asdict(self)


def _line_from_two_points(p1: SwingPoint, p2: SwingPoint) -> tuple[float, float]:
    """Compute slope and intercept from two swing points."""
    if p2.index == p1.index:
        return 0.0, p1.price
    slope = (p2.price - p1.price) / (p2.index - p1.index)
    intercept = p1.price - slope * p1.index
    return slope, intercept


def _count_touches(
    df: pd.DataFrame,
    slope: float,
    intercept: float,
    trendline_type: TrendlineType,
    tolerance_pct: float = 0.005,
    start_idx: int | None = None,
    end_idx: int | None = None,
) -> tuple[int, list[int]]:
    """Count how many bars touch the trendline within tolerance.

    For a support line, a 'touch' occurs when `low` comes within
    tolerance of the line (from above). Similarly for resistance with `high`.

    A line that is VIOLATED (price crossed it meaningfully) in the middle
    of the fitting range is penalized — we only count valid touches, not
    break points.
    """
    if start_idx is None:
        start_idx = 0
    if end_idx is None:
        end_idx = len(df) - 1

    touches: list[int] = []

    for i in range(start_idx, end_idx + 1):
        line_price = slope * i + intercept

        if trendline_type == "support":
            bar_low = df["low"].iloc[i]
            bar_close = df["close"].iloc[i]
            diff_pct = abs(bar_low - line_price) / line_price if line_price > 0 else 1.0
            # Touch: low within tolerance AND close is above (not broken)
            if diff_pct <= tolerance_pct and bar_close >= line_price * (1 - tolerance_pct):
                touches.append(i)
        else:  # resistance
            bar_high = df["high"].iloc[i]
            bar_close = df["close"].iloc[i]
            diff_pct = abs(bar_high - line_price) / line_price if line_price > 0 else 1.0
            if diff_pct <= tolerance_pct and bar_close <= line_price * (1 + tolerance_pct):
                touches.append(i)

    return len(touches), touches


def _count_violations(
    df: pd.DataFrame,
    slope: float,
    intercept: float,
    trendline_type: TrendlineType,
    violation_pct: float = 0.01,
    start_idx: int | None = None,
    end_idx: int | None = None,
) -> int:
    """Count how many bars violated (broke through) the line meaningfully."""
    if start_idx is None:
        start_idx = 0
    if end_idx is None:
        end_idx = len(df) - 1

    violations = 0
    for i in range(start_idx, end_idx + 1):
        line_price = slope * i + intercept
        if trendline_type == "support":
            bar_close = df["close"].iloc[i]
            if bar_close < line_price * (1 - violation_pct):
                violations += 1
        else:
            bar_close = df["close"].iloc[i]
            if bar_close > line_price * (1 + violation_pct):
                violations += 1
    return violations


def fit_trendlines(
    df: pd.DataFrame,
    swings: list[SwingPoint],
    *,
    min_touches: int = 3,
    tolerance_pct: float = 0.005,
    max_violations_ratio: float = 0.05,
    top_k: int = 20,
) -> list[Trendline]:
    """Fit trendlines from swing points.

    Args:
        df: OHLCV DataFrame (must include 'high', 'low', 'close')
        swings: List of SwingPoint objects from detect_swings()
        min_touches: Minimum number of bars that must touch the line.
        tolerance_pct: Fraction (0.005 = 0.5%) for touch detection.
        max_violations_ratio: Reject lines where violations exceed this
                              fraction of the total bar span.
        top_k: Return at most this many top-scored lines.

    Returns:
        List of Trendline objects sorted by score (descending).
    """
    df = _normalize_ohlcv_columns(df)

    highs = [s for s in swings if s.type == "high"]
    lows = [s for s in swings if s.type == "low"]

    candidates: list[Trendline] = []

    # Support lines: from pairs of low swings
    for p1, p2 in combinations(lows, 2):
        if p2.index <= p1.index:
            continue
        slope, intercept = _line_from_two_points(p1, p2)
        # Support lines should not have absurd slopes
        touch_count, touch_indices = _count_touches(
            df, slope, intercept, "support",
            tolerance_pct=tolerance_pct,
            start_idx=p1.index, end_idx=len(df) - 1,
        )
        if touch_count < min_touches:
            continue
        violations = _count_violations(
            df, slope, intercept, "support",
            violation_pct=tolerance_pct * 2,
            start_idx=p1.index, end_idx=p2.index,
        )
        span = p2.index - p1.index
        if span > 0 and violations / span > max_violations_ratio:
            continue
        candidates.append(Trendline(
            type="support",
            slope=slope,
            intercept=intercept,
            start_index=p1.index,
            end_index=p2.index,
            start_date=p1.date,
            end_date=p2.date,
            touch_count=touch_count,
            touch_indices=touch_indices,
        ))

    # Resistance lines: from pairs of high swings
    for p1, p2 in combinations(highs, 2):
        if p2.index <= p1.index:
            continue
        slope, intercept = _line_from_two_points(p1, p2)
        touch_count, touch_indices = _count_touches(
            df, slope, intercept, "resistance",
            tolerance_pct=tolerance_pct,
            start_idx=p1.index, end_idx=len(df) - 1,
        )
        if touch_count < min_touches:
            continue
        violations = _count_violations(
            df, slope, intercept, "resistance",
            violation_pct=tolerance_pct * 2,
            start_idx=p1.index, end_idx=p2.index,
        )
        span = p2.index - p1.index
        if span > 0 and violations / span > max_violations_ratio:
            continue
        candidates.append(Trendline(
            type="resistance",
            slope=slope,
            intercept=intercept,
            start_index=p1.index,
            end_index=p2.index,
            start_date=p1.date,
            end_date=p2.date,
            touch_count=touch_count,
            touch_indices=touch_indices,
        ))

    # Score all candidates (imported here to avoid circular reference)
    from .scorer import score_trendline
    for tl in candidates:
        tl.score = score_trendline(tl, df)

    # Sort by score descending and return top-K
    candidates.sort(key=lambda t: t.score, reverse=True)
    return candidates[:top_k]
