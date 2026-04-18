"""Trendline fitting and scoring module."""
from .fitter import Trendline, fit_trendlines
from .scorer import score_trendline

__all__ = ["Trendline", "fit_trendlines", "score_trendline"]
