"""Tests for swing detection."""
import numpy as np
import pandas as pd
import pytest

from src.swings.detector import (
    SwingPoint,
    detect_swings,
    detect_swings_with_atr_filter,
    _enforce_alternation,
)


def _make_sine_wave_df(n: int = 100, amplitude: float = 10.0, period: int = 20) -> pd.DataFrame:
    """Create a clean OHLCV dataframe that's a sine wave (predictable swings)."""
    t = np.arange(n)
    base = 100 + amplitude * np.sin(2 * np.pi * t / period)
    return pd.DataFrame({
        "open": base,
        "high": base + 0.5,
        "low": base - 0.5,
        "close": base,
        "volume": np.ones(n) * 1000,
    }, index=pd.date_range("2024-01-01", periods=n, freq="D"))


class TestDetectSwings:
    def test_detects_sine_wave_peaks_and_troughs(self):
        df = _make_sine_wave_df(n=100, period=20)
        swings = detect_swings(df, distance=5)
        # A sine wave of period 20 over 100 bars has ~5 peaks and ~5 troughs
        assert len(swings) >= 8, f"Expected at least 8 swings, got {len(swings)}"

    def test_alternation_enforced(self):
        df = _make_sine_wave_df(n=100, period=20)
        swings = detect_swings(df, distance=5)
        for i in range(len(swings) - 1):
            assert swings[i].type != swings[i + 1].type, (
                f"Adjacent swings have same type: {swings[i]} / {swings[i+1]}"
            )

    def test_chronological_order(self):
        df = _make_sine_wave_df(n=100, period=20)
        swings = detect_swings(df, distance=5)
        for i in range(len(swings) - 1):
            assert swings[i].index < swings[i + 1].index

    def test_handles_flat_data(self):
        df = pd.DataFrame({
            "open": [100] * 50,
            "high": [100] * 50,
            "low": [100] * 50,
            "close": [100] * 50,
        })
        swings = detect_swings(df, distance=5)
        # Flat data = few or no swings
        assert len(swings) <= 2

    def test_atr_filter_reduces_noise(self):
        # Add small noise to sine wave
        df = _make_sine_wave_df(n=100, period=20)
        np.random.seed(42)
        noise = np.random.randn(len(df)) * 0.3
        df["high"] += noise
        df["low"] += noise
        df["close"] += noise

        unfiltered = detect_swings(df, distance=3)
        filtered = detect_swings_with_atr_filter(df, distance=3, atr_multiplier=1.5)
        assert len(filtered) <= len(unfiltered), "ATR filter should reduce swing count"

    def test_missing_columns_raises(self):
        bad_df = pd.DataFrame({"price": [1, 2, 3]})
        with pytest.raises(ValueError, match="missing required columns"):
            detect_swings(bad_df)


class TestEnforceAlternation:
    def test_removes_consecutive_same_type(self):
        swings = [
            SwingPoint(0, "2024-01-01", 100.0, "low", 1.0),
            SwingPoint(5, "2024-01-06", 105.0, "high", 1.0),
            SwingPoint(10, "2024-01-11", 110.0, "high", 1.5),   # keep this one (more extreme)
            SwingPoint(15, "2024-01-16", 95.0, "low", 1.0),
        ]
        result = _enforce_alternation(swings)
        assert len(result) == 3
        assert result[1].price == 110.0  # kept the more extreme high

    def test_empty_input(self):
        assert _enforce_alternation([]) == []

    def test_single_swing(self):
        s = SwingPoint(0, "2024-01-01", 100.0, "low", 1.0)
        assert _enforce_alternation([s]) == [s]
