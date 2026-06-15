from __future__ import annotations

import pytest

from analysis.event_finder import apply_fault_wrist_rotation, find_swing_phases


def _fixture_samples() -> list[dict]:
    return [
        {
            "timestamp": 0.0,
            "accelX": 0.1,
            "accelY": 0.0,
            "accelZ": 0.2,
            "gyroX": 1.0,
            "gyroY": 0.1,
            "gyroZ": 0.1,
            "pitch": 0.01,
            "roll": 0.0,
            "yaw": 0.0,
        },
        {
            "timestamp": 0.2,
            "accelX": 0.5,
            "accelY": 0.3,
            "accelZ": 0.4,
            "gyroX": 3.8,
            "gyroY": 0.8,
            "gyroZ": 0.6,
            "pitch": 0.03,
            "roll": 0.05,
            "yaw": 0.02,
        },
        {
            "timestamp": 0.4,
            "accelX": 2.8,
            "accelY": 0.3,
            "accelZ": 0.4,
            "gyroX": 3.2,
            "gyroY": 0.8,
            "gyroZ": 0.6,
            "pitch": 0.04,
            "roll": 0.1,
            "yaw": 0.04,
        },
        {
            "timestamp": 0.55,
            "accelX": 1.2,
            "accelY": 0.2,
            "accelZ": 0.1,
            "gyroX": 2.5,
            "gyroY": 0.5,
            "gyroZ": 0.2,
            "pitch": 0.05,
            "roll": 0.25,
            "yaw": 0.08,
        },
        {
            "timestamp": 0.7,
            "accelX": 0.8,
            "accelY": 0.2,
            "accelZ": 0.1,
            "gyroX": 2.0,
            "gyroY": 0.4,
            "gyroZ": 0.2,
            "pitch": 0.06,
            "roll": 0.4,
            "yaw": 0.12,
        },
        {
            "timestamp": 0.9,
            "accelX": 0.4,
            "accelY": 0.1,
            "accelZ": 0.1,
            "gyroX": 1.5,
            "gyroY": 0.2,
            "gyroZ": 0.1,
            "pitch": 0.07,
            "roll": 0.5,
            "yaw": 0.15,
        },
    ]


def test_find_swing_phases_returns_practice_chain() -> None:
    legacy = [
        {"timestamp": 0.0, "type": "start"},
        {"timestamp": 0.4, "type": "impact"},
        {"timestamp": 0.9, "type": "followThrough"},
    ]
    result = find_swing_phases(_fixture_samples(), legacy)

    assert result["analysisVersion"] == "event_finder_v1"
    assert result["swingMode"] in {"practice", "full"}
    assert result["phaseChainComplete"] is True
    event_types = [event["type"] for event in result["detectedEvents"]]
    assert "address" in event_types
    assert "takeaway" in event_types
    assert "top" in event_types
    assert "downswingStart" in event_types
    assert "finish" in event_types


def test_find_swing_phases_merges_legacy_markers() -> None:
    legacy = [
        {"timestamp": 0.0, "type": "start"},
        {"timestamp": 0.4, "type": "impact"},
        {"timestamp": 0.9, "type": "followThrough"},
    ]
    result = find_swing_phases(_fixture_samples(), legacy)
    events = {event["type"]: event for event in result["detectedEvents"]}

    assert "takeaway" in events
    assert events["contactGuess"]["timestamp"] == pytest.approx(0.4)
    assert events["finish"]["timestamp"] == pytest.approx(0.9)
    assert result["swingMode"] == "full"


def test_apply_fault_wrist_rotation_adds_flag() -> None:
    analysis = {"faultFlags": []}
    updated = apply_fault_wrist_rotation(analysis, 60.0)
    assert "excessive_wrist_roll" in updated["faultFlags"]


def test_empty_samples_returns_empty_analysis() -> None:
    result = find_swing_phases([], [])
    assert result["detectedEvents"] == []
    assert result["phaseChainComplete"] is False
