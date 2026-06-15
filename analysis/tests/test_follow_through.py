from __future__ import annotations

import math

import pytest

from analysis.follow_through import compute_follow_through_metrics


def test_follow_through_metrics_from_impact_to_finish() -> None:
    samples = [
        {"timestamp": 0.0, "roll": 0.0, "pitch": 0.0, "yaw": 0.0},
        {"timestamp": 0.2, "roll": 0.1, "pitch": 0.0, "yaw": 0.0},
        {"timestamp": 0.4, "roll": 0.2, "pitch": 0.0, "yaw": 0.0},
        {"timestamp": 0.6, "roll": 0.35, "pitch": 0.02, "yaw": 0.08},
        {"timestamp": 0.9, "roll": 0.5, "pitch": 0.05, "yaw": 0.15},
    ]
    markers = [
        {"timestamp": 0.2, "type": "start"},
        {"timestamp": 0.4, "type": "impact"},
        {"timestamp": 0.9, "type": "followThrough"},
    ]

    metrics = compute_follow_through_metrics(samples, markers)

    assert metrics["follow_through_rotation_deg"] == pytest.approx(
        math.degrees(math.sqrt(0.3**2 + 0.15**2 + 0.05**2)), rel=1e-3
    )
    assert metrics["follow_through_roll_deg"] == pytest.approx(math.degrees(0.3), rel=1e-3)
    assert metrics["follow_through_yaw_deg"] == pytest.approx(math.degrees(0.15), rel=1e-3)
    assert metrics["follow_through_direction_label"] is not None
    assert metrics["follow_through"]["path"]["times"][0] == pytest.approx(0.0)


def test_follow_through_metrics_missing_impact() -> None:
    samples = [{"timestamp": 0.0, "roll": 0.0, "pitch": 0.0, "yaw": 0.0}]
    metrics = compute_follow_through_metrics(samples, [])
    assert metrics["follow_through_rotation_deg"] is None
    assert metrics["follow_through"] is None
