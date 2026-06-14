from __future__ import annotations

import sys
from pathlib import Path

import pytest

ANALYSIS_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = ANALYSIS_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from analysis.swing_trim import trim_record, trim_samples  # noqa: E402


NOISY_SWING = {
    "id": "noise-1",
    "samples": [
        {
            "timestamp": 0.0,
            "accelX": 0.02,
            "accelY": 0.01,
            "accelZ": 0.01,
            "gyroX": 0.1,
            "gyroY": 0.05,
            "gyroZ": 0.05,
            "pitch": 0.0,
            "roll": 0.0,
            "yaw": 0.0,
        },
        {
            "timestamp": 0.1,
            "accelX": 0.03,
            "accelY": 0.02,
            "accelZ": 0.02,
            "gyroX": 0.2,
            "gyroY": 0.1,
            "gyroZ": 0.1,
            "pitch": 0.0,
            "roll": 0.0,
            "yaw": 0.0,
        },
        {
            "timestamp": 0.3,
            "accelX": 0.8,
            "accelY": 0.4,
            "accelZ": 0.5,
            "gyroX": 4.0,
            "gyroY": 2.0,
            "gyroZ": 1.5,
            "pitch": 0.1,
            "roll": 0.05,
            "yaw": 0.02,
        },
        {
            "timestamp": 0.5,
            "accelX": 1.2,
            "accelY": 0.6,
            "accelZ": 0.7,
            "gyroX": 5.0,
            "gyroY": 2.5,
            "gyroZ": 1.8,
            "pitch": 0.12,
            "roll": 0.04,
            "yaw": 0.03,
        },
        {
            "timestamp": 0.8,
            "accelX": 0.05,
            "accelY": 0.02,
            "accelZ": 0.02,
            "gyroX": 0.3,
            "gyroY": 0.1,
            "gyroZ": 0.1,
            "pitch": 0.0,
            "roll": 0.0,
            "yaw": 0.0,
        },
    ],
    "eventMarkers": [
        {"timestamp": 0.3, "type": "start"},
        {"timestamp": 0.5, "type": "impact"},
    ],
}


def test_trim_samples_removes_leading_and_trailing_noise() -> None:
    trimmed, meta = trim_samples(NOISY_SWING["samples"])

    assert meta["raw_sample_count"] == 5
    assert meta["trimmed_sample_count"] == 2
    assert trimmed[0]["timestamp"] == pytest.approx(0.0)
    assert trimmed[-1]["timestamp"] == pytest.approx(0.2)
    assert meta["trimmed_leading_seconds"] == pytest.approx(0.3)


def test_trim_record_rebases_markers() -> None:
    trimmed = trim_record(NOISY_SWING)

    assert len(trimmed["samples"]) == 2
    assert trimmed["eventMarkers"] == [
        {"type": "start", "timestamp": pytest.approx(0.0)},
        {"type": "impact", "timestamp": pytest.approx(0.2)},
    ]
