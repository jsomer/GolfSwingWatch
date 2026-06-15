"""Practice-swing phase detection from Apple Watch motion samples."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

ANALYSIS_VERSION = "event_finder_v1"

STILL_GYRO = 2.0
TAKEAWAY_GYRO = 2.8
FINISH_GYRO = 2.0
CONTACT_ACCEL = 2.2
CONTACT_CONFIDENCE_MIN = 0.35
RUSHED_TRANSITION_RATIO = 0.55
EXCESSIVE_WRIST_ROTATION_DEG = 45.0
PAUSE_GYRO = 1.8
PAUSE_MIN_SAMPLES = 2

PHASE_ORDER = ("address", "takeaway", "top", "downswingStart", "finish")


def _magnitude(x: float, y: float, z: float) -> float:
    return math.sqrt((x * x) + (y * y) + (z * z))


def _event(
    event_type: str,
    timestamp: float,
    confidence: float,
    source: str = "rule",
) -> dict[str, Any]:
    return {
        "type": event_type,
        "timestamp": float(timestamp),
        "confidence": float(max(0.0, min(1.0, confidence))),
        "source": source,
    }


def _legacy_markers(markers: list[dict[str, Any]]) -> dict[str, float]:
    resolved: dict[str, float] = {}
    for marker in markers:
        event_type = marker.get("type")
        if not event_type:
            continue
        try:
            resolved[str(event_type)] = float(marker.get("timestamp"))
        except (TypeError, ValueError):
            continue
    return resolved


def _prepare_frame(samples: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(samples)
    for column in (
        "timestamp",
        "accelX",
        "accelY",
        "accelZ",
        "gyroX",
        "gyroY",
        "gyroZ",
        "pitch",
        "roll",
        "yaw",
    ):
        if column not in frame.columns:
            frame[column] = np.nan
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    frame["gyro_mag"] = np.sqrt(frame["gyroX"] ** 2 + frame["gyroY"] ** 2 + frame["gyroZ"] ** 2)
    frame["accel_mag"] = np.sqrt(frame["accelX"] ** 2 + frame["accelY"] ** 2 + frame["accelZ"] ** 2)
    return frame


def _find_address_index(gyro_mag: np.ndarray) -> int:
    if len(gyro_mag) == 0:
        return 0
    still = gyro_mag < STILL_GYRO
    run = 0
    best_end = 0
    for index, is_still in enumerate(still):
        if is_still:
            run += 1
            if run >= PAUSE_MIN_SAMPLES:
                best_end = index
        else:
            run = 0
    if best_end > 0:
        return max(0, best_end - run + 1)
    return 0


def _find_takeaway_index(gyro_mag: np.ndarray, start_index: int) -> int:
    for index in range(max(start_index, 0), len(gyro_mag)):
        if index + 1 >= len(gyro_mag):
            break
        if gyro_mag[index] >= TAKEAWAY_GYRO and gyro_mag[index + 1] >= TAKEAWAY_GYRO:
            return index
    peak_index = int(np.argmax(gyro_mag))
    return min(max(start_index + 1, 0), peak_index)


def _find_top_index(gyro_mag: np.ndarray, takeaway_index: int) -> int:
    if takeaway_index >= len(gyro_mag) - 2:
        return max(takeaway_index, 0)
    search_end = max(takeaway_index + 2, int(len(gyro_mag) * 0.85))
    search_end = min(search_end, len(gyro_mag))
    segment = gyro_mag[takeaway_index:search_end]
    if len(segment) == 0:
        return takeaway_index
    local_min = int(np.argmin(segment))
    return takeaway_index + local_min


def _find_downswing_start_index(gyro_mag: np.ndarray, top_index: int) -> int:
    if top_index >= len(gyro_mag) - 2:
        return top_index
    for index in range(top_index + 1, len(gyro_mag) - 1):
        if gyro_mag[index + 1] > gyro_mag[index] and gyro_mag[index + 1] >= TAKEAWAY_GYRO:
            return index + 1
    peak_index = int(np.argmax(gyro_mag[top_index:])) + top_index
    return max(top_index + 1, min(peak_index, len(gyro_mag) - 1))


def _find_finish_index(gyro_mag: np.ndarray, downswing_index: int) -> int:
    if downswing_index >= len(gyro_mag) - 1:
        return len(gyro_mag) - 1
    peak_index = int(np.argmax(gyro_mag[downswing_index:])) + downswing_index
    for index in range(peak_index, len(gyro_mag)):
        if index + 1 >= len(gyro_mag):
            return len(gyro_mag) - 1
        if gyro_mag[index] < FINISH_GYRO and gyro_mag[index + 1] < FINISH_GYRO:
            return index + 1
    return len(gyro_mag) - 1


def _find_contact_guess(frame: pd.DataFrame, downswing_index: int, finish_index: int) -> dict[str, Any] | None:
    if finish_index <= downswing_index:
        return None
    window = frame.iloc[downswing_index : finish_index + 1]
    if window.empty:
        return None
    peak_row = window.loc[window["accel_mag"].idxmax()]
    baseline = float(window["accel_mag"].median())
    peak = float(peak_row["accel_mag"])
    if peak < CONTACT_ACCEL:
        return None
    confidence = (peak - baseline) / peak if peak > 0 else 0.0
    if confidence < CONTACT_CONFIDENCE_MIN:
        return None
    return _event("contactGuess", float(peak_row["timestamp"]), confidence, source="contactGuess")


def _phase_timestamp(frame: pd.DataFrame, index: int) -> float:
    index = max(0, min(index, len(frame) - 1))
    return float(frame["timestamp"].iloc[index])


def _merge_legacy_events(
    events: list[dict[str, Any]],
    legacy: dict[str, float],
) -> list[dict[str, Any]]:
    mapped = {
        "start": "takeaway",
        "impact": "contactGuess",
        "followThrough": "finish",
    }
    existing = {event["type"]: event for event in events}
    for legacy_type, phase_type in mapped.items():
        if legacy_type not in legacy:
            continue
        if phase_type in existing and existing[phase_type]["confidence"] >= 0.6:
            continue
        confidence = 0.75 if legacy_type != "impact" else 0.5
        existing[phase_type] = _event(phase_type, legacy[legacy_type], confidence, source="legacy")
    ordered: list[dict[str, Any]] = []
    for phase_type in PHASE_ORDER + ("contactGuess",):
        if phase_type in existing:
            ordered.append(existing[phase_type])
    for event in existing.values():
        if event not in ordered:
            ordered.append(event)
    return sorted(ordered, key=lambda item: item["timestamp"])


def _phase_durations(events: dict[str, float]) -> dict[str, float | None]:
    def span(start_key: str, end_key: str) -> float | None:
        start = events.get(start_key)
        end = events.get(end_key)
        if start is None or end is None or end <= start:
            return None
        return float(end - start)

    backswing = span("takeaway", "top")
    downswing = span("top", "finish")
    if downswing is None:
        downswing = span("downswingStart", "finish")
    transition_ratio = None
    if backswing is not None and downswing is not None and downswing > 0:
        transition_ratio = backswing / downswing
    return {
        "backswing_duration_seconds": backswing,
        "downswing_duration_seconds": downswing,
        "transition_ratio": transition_ratio,
    }


def _fault_flags(
    events: dict[str, float],
    phase_metrics: dict[str, float | None],
    gyro_mag: np.ndarray,
    takeaway_index: int,
    top_index: int,
    wrist_rotation_deg: float | None,
) -> list[str]:
    flags: list[str] = []
    ratio = phase_metrics.get("transition_ratio")
    if ratio is not None and ratio < RUSHED_TRANSITION_RATIO:
        flags.append("rushed_transition")
    if wrist_rotation_deg is not None and wrist_rotation_deg > EXCESSIVE_WRIST_ROTATION_DEG:
        flags.append("excessive_wrist_roll")
    if takeaway_index < top_index:
        segment = gyro_mag[takeaway_index:top_index]
        pause_run = 0
        for value in segment:
            if value < PAUSE_GYRO:
                pause_run += 1
                if pause_run >= PAUSE_MIN_SAMPLES:
                    flags.append("mid_swing_pause")
                    break
            else:
                pause_run = 0
    if "finish" not in events:
        flags.append("incomplete_finish")
    return flags


def event_timestamp(events: list[dict[str, Any]], event_type: str) -> float | None:
    for event in events:
        if event.get("type") == event_type:
            try:
                return float(event["timestamp"])
            except (TypeError, ValueError, KeyError):
                return None
    legacy_aliases = {
        "impact": "contactGuess",
        "start": "takeaway",
        "followThrough": "finish",
    }
    alias = legacy_aliases.get(event_type)
    if alias:
        return event_timestamp(events, alias)
    return None


def find_swing_phases(
    samples: list[dict[str, Any]],
    legacy_markers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Detect practice-swing phases and fault flags from motion samples."""
    if not samples:
        return {
            "analysisVersion": ANALYSIS_VERSION,
            "swingMode": "practice",
            "detectedEvents": [],
            "faultFlags": [],
            "phaseMetrics": {},
            "phaseChainComplete": False,
        }

    frame = _prepare_frame(samples)
    gyro_mag = frame["gyro_mag"].to_numpy(dtype=float)
    legacy = _legacy_markers(legacy_markers or [])

    address_index = _find_address_index(gyro_mag)
    takeaway_index = _find_takeaway_index(gyro_mag, address_index)
    top_index = _find_top_index(gyro_mag, takeaway_index)
    if top_index <= takeaway_index:
        top_index = min(takeaway_index + 1, len(frame) - 1)
    downswing_index = _find_downswing_start_index(gyro_mag, top_index)
    finish_index = _find_finish_index(gyro_mag, downswing_index)

    events = [
        _event("address", _phase_timestamp(frame, address_index), 0.8),
        _event("takeaway", _phase_timestamp(frame, takeaway_index), 0.85),
        _event("top", _phase_timestamp(frame, top_index), 0.8),
        _event("downswingStart", _phase_timestamp(frame, downswing_index), 0.75),
        _event("finish", _phase_timestamp(frame, finish_index), 0.8),
    ]
    contact = _find_contact_guess(frame, downswing_index, finish_index)
    if contact is not None:
        events.append(contact)
    events = _merge_legacy_events(events, legacy)

    event_map = {event["type"]: event["timestamp"] for event in events}
    phase_metrics = _phase_durations(event_map)
    phase_chain_complete = all(key in event_map for key in PHASE_ORDER)
    swing_mode = "full" if "contactGuess" in event_map else "practice"

    return {
        "analysisVersion": ANALYSIS_VERSION,
        "swingMode": swing_mode,
        "detectedEvents": events,
        "faultFlags": _fault_flags(
            event_map,
            phase_metrics,
            gyro_mag,
            takeaway_index,
            top_index,
            None,
        ),
        "phaseMetrics": phase_metrics,
        "phaseChainComplete": phase_chain_complete,
    }


def apply_fault_wrist_rotation(analysis: dict[str, Any], wrist_rotation_deg: float | None) -> dict[str, Any]:
    if wrist_rotation_deg is None:
        return analysis
    flags = list(analysis.get("faultFlags", []))
    if wrist_rotation_deg > EXCESSIVE_WRIST_ROTATION_DEG and "excessive_wrist_roll" not in flags:
        flags.append("excessive_wrist_roll")
    analysis["faultFlags"] = flags
    return analysis


def _normalize_export_events(raw_events: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_events, list):
        return []
    normalized: list[dict[str, Any]] = []
    for event in raw_events:
        if not isinstance(event, dict):
            continue
        event_type = event.get("type")
        timestamp = event.get("timestamp")
        if not event_type or timestamp is None:
            continue
        try:
            normalized.append(
                {
                    "type": str(event_type),
                    "timestamp": float(timestamp),
                    "confidence": float(event.get("confidence", 1.0)),
                    "source": str(event.get("source", "export")),
                }
            )
        except (TypeError, ValueError):
            continue
    return sorted(normalized, key=lambda item: item["timestamp"])


def resolve_phase_analysis(
    record: dict[str, Any],
    samples: list[dict[str, Any]],
    legacy_markers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Prefer user-confirmed events from export, then detected export events, then compute."""
    computed = find_swing_phases(samples, legacy_markers)
    confirmed = _normalize_export_events(record.get("confirmedEvents"))
    exported = _normalize_export_events(record.get("detectedEvents"))

    if confirmed:
        events = confirmed
    elif exported:
        events = exported
    else:
        return computed

    event_map = {event["type"]: event["timestamp"] for event in events}
    phase_metrics = _phase_durations(event_map)
    phase_chain_complete = all(key in event_map for key in PHASE_ORDER)
    swing_mode = str(record.get("swingMode") or ("full" if "contactGuess" in event_map else "practice"))
    flaw_tags = record.get("flawTags")
    fault_flags = [str(tag) for tag in flaw_tags] if isinstance(flaw_tags, list) and flaw_tags else computed["faultFlags"]

    return {
        "analysisVersion": record.get("analysisVersion") or computed.get("analysisVersion"),
        "swingMode": swing_mode,
        "detectedEvents": events,
        "faultFlags": fault_flags,
        "phaseMetrics": phase_metrics,
        "phaseChainComplete": phase_chain_complete,
    }
