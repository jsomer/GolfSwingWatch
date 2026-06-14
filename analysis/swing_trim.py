from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


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


def trim_record(record: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    trimmed = deepcopy(record)
    samples = record.get("samples", [])
    ordered = sorted(samples, key=lambda item: item["timestamp"])

    if not ordered:
        trimmed["samples"] = []
        trimmed["eventMarkers"] = []
        return trimmed

    start_idx, end_idx = _find_active_bounds(ordered, **kwargs)
    window_start = ordered[start_idx]["timestamp"]
    window_end = ordered[end_idx]["timestamp"]

    trimmed_samples, _meta = trim_samples(samples, **kwargs)
    trimmed["samples"] = trimmed_samples

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
                "timestamp": marker_time - window_start,
            }
        )
    trimmed["eventMarkers"] = rebased_markers
    return trimmed


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
