from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

MAX_SWING_DURATION_SECONDS = 8.0
PHASE_PRE_PAD_SECONDS = 0.15
PHASE_POST_PAD_SECONDS = 0.25


def _magnitude(x: float, y: float, z: float) -> float:
    return (x * x + y * y + z * z) ** 0.5


def _is_active(
    sample: dict[str, Any],
    accel_threshold: float,
    gyro_threshold: float,
) -> bool:
    accel = _magnitude(sample["accelX"], sample["accelY"], sample["accelZ"])
    gyro = _magnitude(sample["gyroX"], sample["gyroY"], sample["gyroZ"])
    return accel >= accel_threshold or gyro >= gyro_threshold


def _event_time(
    events: list[dict[str, Any]],
    *types: str,
    pick: str = "first",
) -> float | None:
    matches: list[float] = []
    for event_type in types:
        for event in events:
            if event.get("type") == event_type:
                try:
                    matches.append(float(event["timestamp"]))
                except (TypeError, ValueError, KeyError):
                    continue
    if not matches:
        return None
    return min(matches) if pick == "first" else max(matches)


def _events_in_range(
    events: list[dict[str, Any]],
    sample_start: float,
    sample_end: float,
) -> list[dict[str, Any]]:
    in_range: list[dict[str, Any]] = []
    for event in events:
        try:
            timestamp = float(event["timestamp"])
        except (TypeError, ValueError, KeyError):
            continue
        if sample_start <= timestamp <= sample_end:
            in_range.append(event)
    return in_range


def _cap_window(
    window_start: float,
    window_end: float,
    core_start: float,
    core_end: float,
    max_duration: float,
    sample_start: float,
    sample_end: float,
) -> tuple[float, float]:
    duration = window_end - window_start
    if duration <= max_duration:
        return window_start, window_end
    core_center = (core_start + core_end) / 2.0
    half = max_duration / 2.0
    window_start = max(sample_start, core_center - half)
    window_end = min(sample_end, core_center + half)
    if window_end - window_start > max_duration:
        window_end = window_start + max_duration
    if window_end - window_start < max_duration and window_end < sample_end:
        window_end = min(sample_end, window_start + max_duration)
    return window_start, window_end


def _phase_window(
    events: list[dict[str, Any]],
    sample_start: float,
    sample_end: float,
    *,
    max_duration: float,
    pre_pad: float,
    post_pad: float,
) -> tuple[float, float] | None:
    in_range = _events_in_range(events, sample_start, sample_end)
    phase_start = _event_time(in_range, "address", "takeaway", "start", pick="first")
    phase_end = _event_time(in_range, "finish", "followThrough", pick="last")
    if phase_start is None or phase_end is None or phase_end <= phase_start:
        return None
    window_start = max(sample_start, phase_start - pre_pad)
    window_end = min(sample_end, phase_end + post_pad)
    return _cap_window(
        window_start,
        window_end,
        phase_start,
        phase_end,
        max_duration,
        sample_start,
        sample_end,
    )


def _find_active_bounds(
    samples: list[dict[str, Any]],
    *,
    accel_fraction: float = 0.15,
    gyro_fraction: float = 0.15,
    min_accel: float = 0.25,
    min_gyro: float = 1.0,
    window: int = 3,
    pre_pad_seconds: float = 0.05,
    post_pad_seconds: float = 0.1,
) -> tuple[int, int]:
    if not samples:
        return 0, -1
    if len(samples) == 1:
        return 0, 0

    accel_mags = [
        _magnitude(s["accelX"], s["accelY"], s["accelZ"]) for s in samples
    ]
    gyro_mags = [
        _magnitude(s["gyroX"], s["gyroY"], s["gyroZ"]) for s in samples
    ]
    peak_accel = max(accel_mags)
    peak_gyro = max(gyro_mags)
    accel_threshold = max(peak_accel * accel_fraction, min_accel)
    gyro_threshold = max(peak_gyro * gyro_fraction, min_gyro)

    active = [
        _is_active(sample, accel_threshold, gyro_threshold) for sample in samples
    ]

    start_idx = 0
    for idx in range(0, len(active) - window + 1):
        if all(active[idx : idx + window]):
            start_idx = idx
            break
    else:
        for idx, is_active in enumerate(active):
            if is_active:
                start_idx = idx
                break

    end_idx = len(samples) - 1
    for idx in range(len(active) - window, -1, -1):
        if all(active[idx : idx + window]):
            end_idx = idx + window - 1
            break
    else:
        for idx in range(len(active) - 1, -1, -1):
            if active[idx]:
                end_idx = idx
                break

    if end_idx < start_idx:
        return 0, len(samples) - 1

    start_time = samples[start_idx]["timestamp"]
    end_time = samples[end_idx]["timestamp"]
    pad_start_time = start_time - pre_pad_seconds
    pad_end_time = end_time + post_pad_seconds

    while start_idx > 0 and samples[start_idx - 1]["timestamp"] >= pad_start_time:
        start_idx -= 1
    while end_idx < len(samples) - 1 and samples[end_idx + 1]["timestamp"] <= pad_end_time:
        end_idx += 1

    return start_idx, end_idx


def _active_window_with_cap(
    samples: list[dict[str, Any]],
    *,
    max_duration: float,
    **kwargs: Any,
) -> tuple[float, float]:
    ordered = sorted(samples, key=lambda item: item["timestamp"])
    start_idx, end_idx = _find_active_bounds(ordered, **kwargs)
    window_start = ordered[start_idx]["timestamp"]
    window_end = ordered[end_idx]["timestamp"]
    sample_start = ordered[0]["timestamp"]
    sample_end = ordered[-1]["timestamp"]
    peak_idx = max(range(start_idx, end_idx + 1), key=lambda idx: _magnitude(
        ordered[idx]["gyroX"],
        ordered[idx]["gyroY"],
        ordered[idx]["gyroZ"],
    ))
    core_time = ordered[peak_idx]["timestamp"]
    return _cap_window(
        window_start,
        window_end,
        core_time,
        core_time,
        max_duration,
        sample_start,
        sample_end,
    )


def _resolve_phase_events(record: dict[str, Any]) -> list[dict[str, Any]]:
    confirmed = record.get("confirmedEvents")
    if isinstance(confirmed, list) and confirmed:
        return confirmed
    detected = record.get("detectedEvents")
    if isinstance(detected, list) and detected:
        return detected
    try:
        from analysis.event_finder import find_swing_phases
    except ImportError:
        from event_finder import find_swing_phases
    analysis = find_swing_phases(
        record.get("samples", []),
        record.get("eventMarkers", []),
    )
    return analysis.get("detectedEvents", [])


def _apply_time_window(
    record: dict[str, Any],
    window_start: float,
    window_end: float,
) -> dict[str, Any]:
    trimmed = deepcopy(record)
    ordered = sorted(record.get("samples", []), key=lambda item: item["timestamp"])
    if not ordered:
        trimmed["samples"] = []
        trimmed["eventMarkers"] = []
        return trimmed

    clipped = [
        sample
        for sample in ordered
        if window_start <= sample["timestamp"] <= window_end
    ]
    if not clipped:
        clipped = ordered

    base_time = clipped[0]["timestamp"]
    trimmed["samples"] = [
        dict(sample, timestamp=sample["timestamp"] - base_time) for sample in clipped
    ]

    rebased_markers = []
    for marker in record.get("eventMarkers", []):
        try:
            marker_time = float(marker.get("timestamp", 0.0))
        except (TypeError, ValueError):
            continue
        if marker_time < window_start or marker_time > window_end:
            continue
        rebased_markers.append(
            {
                "type": marker.get("type"),
                "timestamp": marker_time - base_time,
            }
        )
    trimmed["eventMarkers"] = rebased_markers

    for key in ("detectedEvents", "confirmedEvents"):
        events = record.get(key)
        if not isinstance(events, list):
            continue
        rebased_events = []
        for event in events:
            if not isinstance(event, dict):
                continue
            try:
                event_time = float(event["timestamp"])
            except (TypeError, ValueError, KeyError):
                continue
            if event_time < window_start or event_time > window_end:
                continue
            rebased = dict(event)
            rebased["timestamp"] = event_time - base_time
            rebased_events.append(rebased)
        trimmed[key] = rebased_events

    return trimmed


def trim_samples(
    samples: list[dict[str, Any]],
    **kwargs: Any,
) -> tuple[list[dict[str, Any]], dict[str, float | int]]:
    ordered = sorted(samples, key=lambda item: item["timestamp"])
    if not ordered:
        return [], {
            "raw_sample_count": 0,
            "trimmed_sample_count": 0,
            "trimmed_leading_seconds": 0.0,
            "trimmed_trailing_seconds": 0.0,
        }

    start_idx, end_idx = _find_active_bounds(ordered, **kwargs)
    trimmed = ordered[start_idx : end_idx + 1]
    base_time = trimmed[0]["timestamp"]

    rebased = [dict(sample, timestamp=sample["timestamp"] - base_time) for sample in trimmed]

    raw_duration = ordered[-1]["timestamp"] - ordered[0]["timestamp"]
    trimmed_duration = trimmed[-1]["timestamp"] - trimmed[0]["timestamp"]
    leading = max(0.0, trimmed[0]["timestamp"] - ordered[0]["timestamp"])
    trailing = max(0.0, ordered[-1]["timestamp"] - trimmed[-1]["timestamp"])

    return rebased, {
        "raw_sample_count": len(ordered),
        "trimmed_sample_count": len(rebased),
        "trimmed_leading_seconds": leading,
        "trimmed_trailing_seconds": trailing,
        "trimmed_duration_seconds": trimmed_duration,
        "raw_duration_seconds": raw_duration,
    }


def trim_record(
    record: dict[str, Any],
    *,
    phase_trim: bool = True,
    max_duration_seconds: float = MAX_SWING_DURATION_SECONDS,
    **kwargs: Any,
) -> dict[str, Any]:
    samples = record.get("samples", [])
    ordered = sorted(samples, key=lambda item: item["timestamp"])
    if not ordered:
        trimmed = deepcopy(record)
        trimmed["samples"] = []
        trimmed["eventMarkers"] = []
        return trimmed

    sample_start = ordered[0]["timestamp"]
    sample_end = ordered[-1]["timestamp"]
    window: tuple[float, float] | None = None

    if phase_trim:
        events = _resolve_phase_events(record)
        if events:
            candidate = _phase_window(
                events,
                sample_start,
                sample_end,
                max_duration=max_duration_seconds,
                pre_pad=PHASE_PRE_PAD_SECONDS,
                post_pad=PHASE_POST_PAD_SECONDS,
            )
            if candidate is not None and candidate[1] > candidate[0]:
                window = candidate

    if window is None:
        window = _active_window_with_cap(
            ordered,
            max_duration=max_duration_seconds,
            **kwargs,
        )

    return _apply_time_window(record, window[0], window[1])


def trim_records(records: list[dict[str, Any]], **kwargs: Any) -> list[dict[str, Any]]:
    return [trim_record(record, **kwargs) for record in records]


def trim_json_file(path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "records" in payload:
        records = payload["records"]
        wrapper = True
    elif isinstance(payload, list):
        records = payload
        wrapper = False
    else:
        raise ValueError("Swing export must be a JSON list or {records: [...]} object.")

    trimmed = trim_records(records)
    output = {"records": trimmed} if wrapper else trimmed
    path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    return len(trimmed)
