from __future__ import annotations

import sys
from pathlib import Path

import pytest

ANALYSIS_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = ANALYSIS_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from analysis.event_finder import find_swing_phases  # noqa: E402
from analysis.swing_trim import MAX_SWING_DURATION_SECONDS, trim_record  # noqa: E402


def _long_practice_swing() -> dict:
    samples = []
    for index in range(600):
        timestamp = index * 0.02
        active = 5.0 <= timestamp <= 7.5
        gyro = 4.0 if active else 0.2
        samples.append(
            {
                "timestamp": timestamp,
                "accelX": 0.05,
                "accelY": 0.05,
                "accelZ": 0.05,
                "gyroX": gyro,
                "gyroY": 0.1,
                "gyroZ": 0.1,
                "pitch": 0.01,
                "roll": 0.0,
                "yaw": 0.0,
            }
        )

    phases = find_swing_phases(samples, [])
    return {
        "id": "long-1",
        "samples": samples,
        "eventMarkers": [],
        "detectedEvents": phases["detectedEvents"],
    }


def test_phase_trim_caps_duration_for_long_buffer() -> None:
    record = _long_practice_swing()
    raw_duration = record["samples"][-1]["timestamp"] - record["samples"][0]["timestamp"]
    assert raw_duration > MAX_SWING_DURATION_SECONDS

    trimmed = trim_record(record)
    trimmed_duration = trimmed["samples"][-1]["timestamp"] - trimmed["samples"][0]["timestamp"]
    assert trimmed_duration <= MAX_SWING_DURATION_SECONDS + 0.05
    assert len(trimmed["samples"]) < len(record["samples"])
