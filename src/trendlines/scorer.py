"""Trendline quality scoring.

A good trendline should have:
    1. Many touches (more touches = stronger evidence)
    2. Long time span (spans across significant history)
    3. Recency (more recent touches carry more weight)
    4. Low slope-to-scale ratio (not absurdly steep)
    5. Consistent behavior (no major violations)

Score is normalized to [0, 1].
"""
from __future__ import annotations

import pandas as pd


def score_trendline(tl, df: pd.DataFrame) -> float:
    """Compute composite score for a trendline in [0, 1]."""
    total_bars = len(df)
    if total_bars == 0:
        return 0.0

    # Component 1: touch count (saturates at 8 touches = max)
    touch_score = min(tl.touch_count / 8.0, 1.0)

    # Component 2: time span as fraction of total (saturates at 60%)
    span = tl.end_index - tl.start_index
    span_score = min(span / (total_bars * 0.6), 1.0)

    # Component 3: recency — how recent is the last touch?
    last_touch = max(tl.touch_indices) if tl.touch_indices else tl.end_index
    bars_since_last_touch = total_bars - 1 - last_touch
    # Touches within last 20% of bars get full recency score
    recency_threshold = max(1, total_bars * 0.2)
    recency_score = max(0.0, 1.0 - bars_since_last_touch / recency_threshold)

    # Component 4: slope sanity — penalize near-vertical lines
    # Typical daily prices: a "reasonable" slope is under 5% of mean price per bar
    mean_price = float(df["close"].mean())
    if mean_price > 0:
        slope_ratio = abs(tl.slope) / mean_price
        # Penalize slopes > 2% per bar (very steep)
        slope_score = 1.0 if slope_ratio < 0.02 else max(0.0, 1.0 - (slope_ratio - 0.02) * 50)
    else:
        slope_score = 0.5

    # Weighted average
    weights = {
        "touches":  0.35,
        "span":     0.25,
        "recency":  0.30,
        "slope":    0.10,
    }
    score = (
        weights["touches"] * touch_score
        + weights["span"] * span_score
        + weights["recency"] * recency_score
        + weights["slope"] * slope_score
    )
    return round(score, 4)
