"""Swing high/low detection using scipy.signal.find_peaks + ATR filter.

Strategy:
    1. Find local extrema with scipy.signal.find_peaks (distance parameter).
    2. Optional ATR filter: keep only swings where price movement from
       the previous swing exceeds N * ATR (noise reduction).
    3. Alternating rule: high should follow low and vice versa; remove
       consecutive same-type extrema by keeping only the most extreme.

This is the foundation for trendline fitting and Elliott wave labeling.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Literal

import numpy as np
import pandas as pd
from scipy.signal import find_peaks


SwingType = Literal["high", "low"]


@dataclass(frozen=True)
class SwingPoint:
    """A single swing high or swing low."""

    index: int          # integer index into the source OHLCV dataframe
    date: str           # ISO date string (YYYY-MM-DD) if available
    price: float        # price at the swing (high for 'high', low for 'low')
    type: SwingType     # 'high' or 'low'
    prominence: float   # scipy prominence score (how much it stands out)

    def to_dict(self) -> dict:
        return asdict(self)


def _compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range — a volatility measure."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)

    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    return tr.rolling(window=period, min_periods=1).mean()


def _normalize_ohlcv_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Accept both 'Open' and 'open' column naming; always return lowercase."""
    rename_map = {c: c.lower() for c in df.columns if c.lower() in
                  {"open", "high", "low", "close", "volume", "adj close"}}
    out = df.rename(columns=rename_map)
    required = {"high", "low", "close"}
    missing = required - set(out.columns)
    if missing:
        raise ValueError(
            f"DataFrame missing required columns: {missing}. "
            f"Got: {list(out.columns)}"
        )
    return out


def _extract_dates(df: pd.DataFrame) -> list[str]:
    """Return ISO date strings for each row, using the index if it's datetime."""
    if isinstance(df.index, pd.DatetimeIndex):
        return [d.strftime("%Y-%m-%d") for d in df.index]
    # Fallback: string representation
    return [str(i) for i in df.index]


def detect_swings(
    df: pd.DataFrame,
    *,
    distance: int = 5,
    prominence: float | None = None,
) -> list[SwingPoint]:
    """Detect swing highs and lows using scipy.signal.find_peaks.

    Args:
        df: OHLCV DataFrame with at least 'high' and 'low' columns.
        distance: Minimum number of bars between two swings of the same type.
                  Default 5 works well for daily data.
        prominence: Minimum prominence (price movement) required. If None,
                    scipy auto-selects. Pass an absolute price value.

    Returns:
        List of SwingPoint objects sorted chronologically, with alternating
        high/low types enforced.
    """
    df = _normalize_ohlcv_columns(df)
    dates = _extract_dates(df)

    highs = df["high"].values
    lows = df["low"].values

    # Find peaks (swing highs) and troughs (swing lows)
    # Always pass prominence=(0, None) to ensure 'prominences' key is populated
    prom_arg = prominence if prominence is not None else (0, None)
    peak_idx, peak_props = find_peaks(highs, distance=distance, prominence=prom_arg)
    trough_idx, trough_props = find_peaks(-lows, distance=distance, prominence=prom_arg)

    swings: list[SwingPoint] = []
    for i, idx in enumerate(peak_idx):
        swings.append(SwingPoint(
            index=int(idx),
            date=dates[idx],
            price=float(highs[idx]),
            type="high",
            prominence=float(peak_props["prominences"][i]),
        ))
    for i, idx in enumerate(trough_idx):
        swings.append(SwingPoint(
            index=int(idx),
            date=dates[idx],
            price=float(lows[idx]),
            type="low",
            prominence=float(trough_props["prominences"][i]),
        ))

    # Sort chronologically
    swings.sort(key=lambda s: s.index)

    # Enforce alternation: high must follow low and vice versa.
    # If two consecutive swings have the same type, keep the more extreme one.
    return _enforce_alternation(swings)


def _enforce_alternation(swings: list[SwingPoint]) -> list[SwingPoint]:
    """Remove consecutive same-type swings by keeping only the extreme."""
    if len(swings) <= 1:
        return swings

    result: list[SwingPoint] = [swings[0]]
    for s in swings[1:]:
        prev = result[-1]
        if s.type == prev.type:
            # Same type — keep the more extreme one
            if s.type == "high" and s.price > prev.price:
                result[-1] = s
            elif s.type == "low" and s.price < prev.price:
                result[-1] = s
            # else: current swing is less extreme, drop it
        else:
            result.append(s)
    return result


def detect_swings_with_atr_filter(
    df: pd.DataFrame,
    *,
    distance: int = 5,
    atr_period: int = 14,
    atr_multiplier: float = 1.5,
) -> list[SwingPoint]:
    """Detect swings, then filter out those with sub-ATR moves.

    An ATR-based filter removes "noise swings" — only keep extrema whose
    price movement relative to the previous opposite swing exceeds
    `atr_multiplier * ATR` at that point.

    This dramatically reduces false positives in choppy markets.
    """
    df = _normalize_ohlcv_columns(df)
    atr = _compute_atr(df, period=atr_period)

    raw_swings = detect_swings(df, distance=distance)
    if len(raw_swings) < 2:
        return raw_swings

    # Filter: each swing must move more than atr_multiplier * ATR
    # from the previous opposite-type swing.
    filtered: list[SwingPoint] = [raw_swings[0]]
    for s in raw_swings[1:]:
        prev = filtered[-1]
        price_move = abs(s.price - prev.price)
        atr_at_swing = float(atr.iloc[s.index])
        threshold = atr_at_swing * atr_multiplier

        if price_move >= threshold:
            filtered.append(s)
        # Otherwise drop this swing as noise

    return _enforce_alternation(filtered)
