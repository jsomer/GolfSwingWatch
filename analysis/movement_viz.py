from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from analysis.event_finder import apply_fault_wrist_rotation, find_swing_phases, resolve_phase_analysis
from analysis.follow_through import compute_follow_through_metrics
from analysis.swing_trim import trim_record

DEFAULT_RAW_PATH = Path("data/raw/swings.json")
FALLBACK_RAW_PATH = Path("analysis/tests/fixtures/test_swings.json")


def _load_json_records(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "records" in payload:
        payload = payload["records"]
    if not isinstance(payload, list):
        raise ValueError("Swing export must be a JSON list of records.")
    return payload


def load_raw_swings(path_override: str | None = None) -> list[dict[str, Any]]:
    if path_override:
        return _load_json_records(Path(path_override))
    if DEFAULT_RAW_PATH.exists():
        return _load_json_records(DEFAULT_RAW_PATH)
    if FALLBACK_RAW_PATH.exists():
        return _load_json_records(FALLBACK_RAW_PATH)
    raise FileNotFoundError(
        "No raw swing export found. Import watch data to data/raw/swings.json first."
    )


def find_swing(records: list[dict[str, Any]], swing_id: str) -> dict[str, Any] | None:
    for record in records:
        if str(record.get("id")) == swing_id:
            return record
    return None


def _magnitude(x: float, y: float, z: float) -> float:
    return math.sqrt((x * x) + (y * y) + (z * z))


def _resolve_recommendations(raw_recommendations: Any) -> list[str]:
    if raw_recommendations is None:
        return []
    if isinstance(raw_recommendations, list):
        return [str(item) for item in raw_recommendations if str(item).strip()]
    if isinstance(raw_recommendations, str):
        try:
            parsed = json.loads(raw_recommendations)
            if isinstance(parsed, list):
                return [str(item) for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            stripped = raw_recommendations.strip()
            return [stripped] if stripped else []
    return []


def _markers_for_display(
    start_time: float,
    legacy_markers: list[dict[str, Any]],
    detected_events: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    legacy_display = [
        {
            "type": marker.get("type"),
            "time": float(marker.get("timestamp", 0.0)) - start_time,
            "source": "watch",
        }
        for marker in legacy_markers
    ]
    phase_markers = [
        {
            "type": event.get("type"),
            "time": float(event.get("timestamp", 0.0)) - start_time,
            "confidence": event.get("confidence"),
            "source": event.get("source", "rule"),
        }
        for event in detected_events
    ]
    return legacy_display, phase_markers


def movement_payload(record: dict[str, Any]) -> dict[str, Any]:
    record = trim_record(record)
    samples = sorted(record.get("samples", []), key=lambda item: item["timestamp"])
    legacy_markers = record.get("eventMarkers", [])
    if not samples:
        return {
            "id": record.get("id"),
            "club": record.get("club"),
            "date": record.get("date"),
            "rating": record.get("rating"),
            "sample_count": 0,
            "duration_seconds": 0.0,
            "series": {
                "times": [],
                "accel_mag": [],
                "gyro_mag": [],
                "pitch": [],
                "roll": [],
                "yaw": [],
            },
            "event_markers": [],
            "phase_markers": [],
            "recommendations": _resolve_recommendations(record.get("recommendations")),
            "follow_through": None,
            "swing_mode": "practice",
            "fault_flags": [],
            "phase_metrics": {},
            "phase_chain_complete": False,
        }

    start_time = samples[0]["timestamp"]
    times = [sample["timestamp"] - start_time for sample in samples]

    phase_analysis = resolve_phase_analysis(record, samples, legacy_markers)
    detected_events = phase_analysis["detectedEvents"]
    follow_through = compute_follow_through_metrics(samples, detected_events)
    phase_analysis = apply_fault_wrist_rotation(
        phase_analysis,
        follow_through.get("follow_through_rotation_deg"),
    )
    follow_through_payload = follow_through.get("follow_through")

    event_markers, phase_markers = _markers_for_display(start_time, legacy_markers, detected_events)

    return {
        "id": record.get("id"),
        "club": record.get("club"),
        "date": record.get("date"),
        "rating": record.get("rating"),
        "sample_count": len(samples),
        "duration_seconds": float(times[-1]),
        "series": {
            "times": times,
            "accel_mag": [
                _magnitude(sample["accelX"], sample["accelY"], sample["accelZ"])
                for sample in samples
            ],
            "gyro_mag": [
                _magnitude(sample["gyroX"], sample["gyroY"], sample["gyroZ"])
                for sample in samples
            ],
            "pitch": [sample["pitch"] for sample in samples],
            "roll": [sample["roll"] for sample in samples],
            "yaw": [sample["yaw"] for sample in samples],
        },
        "event_markers": event_markers,
        "phase_markers": phase_markers,
        "recommendations": _resolve_recommendations(record.get("recommendations")),
        "follow_through": follow_through_payload,
        "swing_mode": phase_analysis.get("swingMode"),
        "fault_flags": phase_analysis.get("faultFlags", []),
        "phase_metrics": phase_analysis.get("phaseMetrics", {}),
        "phase_chain_complete": bool(phase_analysis.get("phaseChainComplete")),
        "analysis_version": phase_analysis.get("analysisVersion"),
    }


def movement_catalog(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    catalog = []
    for record in records:
        samples = record.get("samples", [])
        duration = 0.0
        if samples:
            ordered = sorted(samples, key=lambda item: item["timestamp"])
            duration = float(ordered[-1]["timestamp"] - ordered[0]["timestamp"])
        catalog.append(
            {
                "id": str(record.get("id")),
                "club": record.get("club"),
                "date": record.get("date"),
                "rating": record.get("rating"),
                "sample_count": len(samples),
                "duration_seconds": duration,
            }
        )
    return catalog
