"""CLI entry point for trendline-detector.

Usage:
    python -m src.detect --ticker NVDA --days 180
    python -m src.detect --ticker SPY --days 365 --output output/spy.json
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    print("⚠️  yfinance not installed. Install with: pip install yfinance")
    yf = None

from .swings import detect_swings_with_atr_filter
from .trendlines import fit_trendlines
from .elliott import label_elliott_wave
from .export import build_detection_result, save_to_json


def fetch_ohlcv(ticker: str, days: int):
    """Fetch OHLCV data via yfinance."""
    if yf is None:
        raise RuntimeError("yfinance required for data fetch. Install first.")
    import pandas as pd
    period = f"{days}d" if days <= 729 else "2y"
    df = yf.download(ticker, period=period, progress=False, auto_adjust=False)
    if df is None or len(df) == 0:
        raise ValueError(f"No data returned for {ticker}")
    # Flatten multi-level columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    return df


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect swings, trendlines, and Elliott waves in price data",
    )
    parser.add_argument("--ticker", required=True, help="e.g., NVDA, SPY, BTC-USD")
    parser.add_argument("--days", type=int, default=180, help="Lookback days (default 180)")
    parser.add_argument("--distance", type=int, default=5, help="Min bars between swings")
    parser.add_argument("--atr-mult", type=float, default=1.5, help="ATR filter multiplier")
    parser.add_argument("--output", default=None, help="Output JSON path")
    parser.add_argument("--no-elliott", action="store_true", help="Skip Elliott Wave labeling")
    parser.add_argument("--min-touches", type=int, default=3, help="Min touches for trendlines")
    args = parser.parse_args()

    print(f"🔍 Fetching {args.ticker} ({args.days} days)...")
    try:
        df = fetch_ohlcv(args.ticker, args.days)
    except Exception as e:
        print(f"❌ Fetch failed: {e}")
        return 1
    print(f"  → {len(df)} bars received")

    print("📍 Detecting swings...")
    swings = detect_swings_with_atr_filter(
        df,
        distance=args.distance,
        atr_multiplier=args.atr_mult,
    )
    print(f"  → {len(swings)} swings detected (after ATR filter)")

    print("📏 Fitting trendlines...")
    trendlines = fit_trendlines(
        df, swings,
        min_touches=args.min_touches,
        top_k=10,
    )
    print(f"  → {len(trendlines)} trendlines retained (top 10)")
    for tl in trendlines[:5]:
        print(f"    [{tl.type:10s}] slope={tl.slope:+.3f} touches={tl.touch_count} score={tl.score:.2f}")

    elliott = None
    if not args.no_elliott:
        print("🌊 Labeling Elliott Wave...")
        elliott = label_elliott_wave(swings)
        print(f"  → pattern={elliott.pattern}, direction={elliott.direction}, "
              f"current={elliott.current_wave}, confidence={elliott.confidence}")

    # Build result
    result = build_detection_result(
        ticker=args.ticker,
        timeframe="daily",
        swings=swings,
        trendlines=trendlines,
        elliott=elliott,
        data_start_date=swings[0].date if swings else None,
        data_end_date=swings[-1].date if swings else None,
    )

    # Output
    output_path = args.output or f"output/{args.ticker}_detection.json"
    save_to_json(result, output_path)
    print(f"\n✅ Saved to {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
