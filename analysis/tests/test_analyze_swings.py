from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ANALYSIS_DIR = Path(__file__).resolve().parents[1]
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))

import analyze_swings  # noqa: E402


FIXTURE_PATH = ANALYSIS_DIR / "tests" / "fixtures" / "test_swings.json"


def test_extract_features_from_fixture_record() -> None:
    records = analyze_swings.load_records(FIXTURE_PATH)
    result = analyze_swings.extract_features(records[0])

    assert result["id"] == "test-1"
    assert result["sample_count"] == 6
    assert result["duration_seconds"] == pytest.approx(0.9)
    assert result["time_to_impact_seconds"] == pytest.approx(0.4)
    assert result["follow_through_seconds"] == pytest.approx(0.5)
    assert result["tempo_source"] == "phase"
    assert result["tempo_ratio"] == result["phase_transition_ratio"]
    assert result["tempo_ratio"] is not None
    assert result["peak_accel_g"] > 0
    assert result["peak_rotational_velocity"] > 0
    assert 0 < result["swing_plane_stability"] <= 1
    assert json.loads(result["recommendations"]) == [
        "Keep your tempo smooth through impact.",
        "Maintain posture during follow-through.",
    ]
    assert result["follow_through_rotation_deg"] is not None
    assert result["follow_through_roll_deg"] is not None
    assert result["swing_mode"] in {"practice", "full"}
    assert result["analysis_version"] == "event_finder_v1"
    assert isinstance(json.loads(result["detected_events"]), list)
    assert isinstance(json.loads(result["fault_flags"]), list)


def test_extract_features_without_recommendations() -> None:
    records = analyze_swings.load_records(FIXTURE_PATH)
    record = dict(records[0])
    record.pop("recommendations", None)
    result = analyze_swings.extract_features(record)
    assert json.loads(result["recommendations"]) == []


def test_cli_writes_csv_and_parquet(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"

    subprocess.run(
        [
            sys.executable,
            str(ANALYSIS_DIR / "analyze_swings.py"),
            "--input",
            str(FIXTURE_PATH),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
    )

    csv_path = output_dir / "swing_features.csv"
    parquet_path = output_dir / "swing_features.parquet"
    assert csv_path.exists()
    assert parquet_path.exists()

    df = pd.read_csv(csv_path)
    assert len(df) == 1
    assert df.loc[0, "id"] == "test-1"
    assert df.loc[0, "sample_count"] == 6
