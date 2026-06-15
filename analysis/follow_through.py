"""Wrist rotation metrics from a swing phase window (practice-first)."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

try:
    from analysis.event_finder import event_timestamp
except ImportError:
    from event_finder import event_timestamp

RAD_TO_DEG = 180.0 / math.pi

AXIS_LABELS = {
    "roll": {1: "Supination (roll +)", -1: "Pronation (roll −)"},
    "yaw": {1: "Yaw left", -1: "Yaw right"},
    "pitch": {1: "Extension (pitch +)", -1: "Flexion (pitch −)"},
}


def _marker_timestamp(markers: list[dict[str, Any]], marker_type: str) -> float | None:
    return event_timestamp(markers, marker_type)


def _unwrap_delta(start: float, end: float) -> float:
    delta = end - start
    return float((delta + math.pi) % (2 * math.pi) - math.pi)


def _cumulative_unwrap(values: np.ndarray) -> np.ndarray:
    if len(values) == 0:
        return values
    cumulative = [0.0]
    for index in range(1, len(values)):
        cumulative.append(cumulative[-1] + _unwrap_delta(float(values[index - 1]), float(values[index])))
    return np.array(cumulative, dtype=float)


def _direction_label(roll_rad: float, yaw_rad: float, pitch_rad: float) -> str:
    components = {
        "roll": roll_rad,
        "yaw": yaw_rad,
        "pitch": pitch_rad,
    }
    dominant_axis = max(components, key=lambda axis: abs(components[axis]))
    dominant_value = components[dominant_axis]
    if abs(dominant_value) < math.radians(3):
        return "Minimal wrist rotation"
    sign = 1 if dominant_value >= 0 else -1
    primary = AXIS_LABELS[dominant_axis][sign]
    secondary_parts = []
    for axis, value in components.items():
        if axis == dominant_axis or abs(value) < math.radians(8):
            continue
        secondary_parts.append(AXIS_LABELS[axis][1 if value >= 0 else -1].split("(")[0].strip())
    if secondary_parts:
        return f"{primary}, {', '.join(secondary_parts)}"
    return primary


def _resolve_window_times(
    markers: list[dict[str, Any]],
    end_time: float,
) -> tuple[float | None, str | None]:
    """Pick start of wrist-return window: top, downswingStart, impact, or legacy start."""
    for phase_type in ("top", "downswingStart", "contactGuess", "impact", "takeaway", "start"):
        start_time = _marker_timestamp(markers, phase_type)
        if start_time is not None and start_time < end_time:
            return start_time, phase_type
    return None, None


def _empty_metrics() -> dict[str, Any]:
    return {
        "follow_through_roll_deg": None,
        "follow_through_yaw_deg": None,
        "follow_through_pitch_deg": None,
        "follow_through_rotation_deg": None,
        "follow_through_direction_deg": None,
        "follow_through_direction_label": None,
        "follow_through_window_start": None,
        "follow_through": None,
    }


def compute_follow_through_metrics(
    samples: list[dict[str, Any]],
    markers: list[dict[str, Any]],
) -> dict[str, Any]:
    """Measure net wrist rotation from top/downswing through finish."""
    if not samples:
        return _empty_metrics()

    frame = pd.DataFrame(samples)
    for column in ("timestamp", "roll", "pitch", "yaw", "gyroX", "gyroY", "gyroZ"):
        if column not in frame.columns:
            frame[column] = np.nan

    frame = frame.sort_values("timestamp").reset_index(drop=True)
    finish_time = _marker_timestamp(markers, "finish")
    if finish_time is None:
        finish_time = _marker_timestamp(markers, "followThrough")
    if finish_time is None:
        finish_time = float(frame["timestamp"].iloc[-1])

    start_time, window_start = _resolve_window_times(markers, finish_time)
    if start_time is None:
        return _empty_metrics()

    window = frame[(frame["timestamp"] >= start_time) & (frame["timestamp"] <= finish_time)].copy()
    if len(window) < 2:
        return _empty_metrics()

    roll_path = _cumulative_unwrap(window["roll"].to_numpy(dtype=float))
    yaw_path = _cumulative_unwrap(window["yaw"].to_numpy(dtype=float))
    pitch_path = _cumulative_unwrap(window["pitch"].to_numpy(dtype=float))

    roll_rad = float(roll_path[-1])
    yaw_rad = float(yaw_path[-1])
    pitch_rad = float(pitch_path[-1])

    roll_deg = roll_rad * RAD_TO_DEG
    yaw_deg = yaw_rad * RAD_TO_DEG
    pitch_deg = pitch_rad * RAD_TO_DEG
    rotation_deg = float(math.degrees(math.sqrt(roll_rad**2 + yaw_rad**2 + pitch_rad**2)))
    direction_deg = float(math.degrees(math.atan2(yaw_rad, roll_rad)) % 360.0)

    relative_times = (window["timestamp"].to_numpy(dtype=float) - start_time).tolist()
    roll_path_deg = (roll_path * RAD_TO_DEG).tolist()
    yaw_path_deg = (yaw_path * RAD_TO_DEG).tolist()
    pitch_path_deg = (pitch_path * RAD_TO_DEG).tolist()

    return {
        "follow_through_roll_deg": roll_deg,
        "follow_through_yaw_deg": yaw_deg,
        "follow_through_pitch_deg": pitch_deg,
        "follow_through_rotation_deg": rotation_deg,
        "follow_through_direction_deg": direction_deg,
        "follow_through_direction_label": _direction_label(roll_rad, yaw_rad, pitch_rad),
        "follow_through_window_start": window_start,
        "follow_through": {
            "window_start": window_start,
            "start_time": start_time,
            "end_time": finish_time,
            "roll_deg": roll_deg,
            "yaw_deg": yaw_deg,
            "pitch_deg": pitch_deg,
            "rotation_deg": rotation_deg,
            "direction_deg": direction_deg,
            "direction_label": _direction_label(roll_rad, yaw_rad, pitch_rad),
            "path": {
                "times": relative_times,
                "roll_deg": roll_path_deg,
                "yaw_deg": yaw_path_deg,
                "pitch_deg": pitch_path_deg,
            },
        },
    }
