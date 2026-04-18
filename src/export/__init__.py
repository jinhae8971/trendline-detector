"""Export module — combines detections into JSON output."""
from .builder import build_detection_result, save_to_json

__all__ = ["build_detection_result", "save_to_json"]
