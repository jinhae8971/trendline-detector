"""Build unified JSON detection result."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..swings.detector import SwingPoint
from ..trendlines.fitter import Trendline
from ..elliott.labeler import ElliottWave


def build_detection_result(
    ticker: str,
    timeframe: str,
    swings: list[SwingPoint],
    trendlines: list[Trendline],
    elliott: ElliottWave | None,
    *,
    data_start_date: str | None = None,
    data_end_date: str | None = None,
) -> dict:
    """Build unified detection result as JSON-serializable dict."""
    return {
        "ticker": ticker,
        "timeframe": timeframe,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "data_range": {
            "start": data_start_date,
            "end": data_end_date,
        },
        "swings": [s.to_dict() for s in swings],
        "trendlines": [t.to_dict() for t in trendlines],
        "elliott_wave": elliott.to_dict() if elliott else None,
        "summary": {
            "swing_count": len(swings),
            "trendline_count": len(trendlines),
            "has_elliott_pattern": bool(elliott and elliott.pattern != "none"),
            "current_wave": elliott.current_wave if elliott else None,
        },
        "schema_version": "0.1.0",
    }


def save_to_json(result: dict, path: str | Path) -> None:
    """Save detection result to a JSON file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
