"""Swing high/low detection module."""
from .detector import (
    SwingPoint,
    detect_swings,
    detect_swings_with_atr_filter,
)

__all__ = ["SwingPoint", "detect_swings", "detect_swings_with_atr_filter"]
