from __future__ import annotations

import pandas as pd

from analysis.pattern_inspector import inspect_patterns


def _sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": "a",
                "date": "2026-06-10",
                "club": "7i",
                "rating": 2,
                "tempo_ratio": 0.4,
                "follow_through_rotation_deg": 55.0,
                "swing_plane_stability": 0.45,
                "fault_flags": '["rushed_transition", "excessive_wrist_roll"]',
                "swing_mode": "practice",
                "phase_chain_complete": True,
            },
            {
                "id": "b",
                "date": "2026-06-11",
                "club": "7i",
                "rating": 2,
                "tempo_ratio": 0.5,
                "follow_through_rotation_deg": 48.0,
                "swing_plane_stability": 0.5,
                "fault_flags": '["rushed_transition"]',
                "swing_mode": "practice",
                "phase_chain_complete": True,
            },
            {
                "id": "c",
                "date": "2026-06-12",
                "club": "Driver",
                "rating": 5,
                "tempo_ratio": 2.8,
                "follow_through_rotation_deg": 20.0,
                "swing_plane_stability": 0.82,
                "fault_flags": "[]",
                "swing_mode": "practice",
                "phase_chain_complete": True,
            },
            {
                "id": "d",
                "date": "2026-06-13",
                "club": "Driver",
                "rating": 4,
                "tempo_ratio": 2.5,
                "follow_through_rotation_deg": 18.0,
                "swing_plane_stability": 0.78,
                "fault_flags": "[]",
                "swing_mode": "full",
                "phase_chain_complete": True,
            },
        ]
    )


def test_detects_shared_fault_in_low_rated_cohort() -> None:
    report = inspect_patterns(_sample_frame())
    fault_patterns = [item for item in report["patterns"] if item["kind"] == "fault"]
    rushed = next(item for item in fault_patterns if item["fault"] == "rushed_transition")
    assert rushed["low_prevalence"] == 1.0
    assert rushed["high_prevalence"] == 0.0


def test_render_markdown_includes_headline_counts() -> None:
    report = inspect_patterns(_sample_frame())
    assert "Swings analyzed" in report["markdown"]
    assert report["low_rated_count"] == 2
    assert report["high_rated_count"] == 2
