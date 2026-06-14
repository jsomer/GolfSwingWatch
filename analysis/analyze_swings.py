#!/usr/bin/env python3
"""Extract baseline features from GolfSwingWatch swing exports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from analysis.swing_trim import trim_record
except ImportError:
    from swing_trim import trim_record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build per-swing feature table from captured swing data."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to swings input (.json, .jsonl, .parquet)",
    )
    parser.add_argument(
        "--output-dir",
        default="analysis/output",
        help="Directory for generated feature files.",
    )
    return parser.parse_args()


def load_records(input_path: Path) -> list[dict[str, Any]]:
    suffix = input_path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and "records" in payload:
            payload = payload["records"]
        if not isinstance(payload, list):
            raise ValueError("JSON input must contain a list of swing records.")
        return payload
    if suffix == ".jsonl":
        lines = [
            line.strip()
            for line in input_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        return [json.loads(line) for line in lines]
    if suffix == ".parquet":
        frame = pd.read_parquet(input_path)
        return frame.to_dict(orient="records")
    raise ValueError(f"Unsupported input format: {suffix}")


def _resolve_event_markers(raw_markers: Any) -> list[dict[str, Any]]:
    if raw_markers is None or (isinstance(raw_markers, float) and np.isnan(raw_markers)):
        return []
    if isinstance(raw_markers, list):
        return raw_markers
    if isinstance(raw_markers, str):
        try:
            parsed = json.loads(raw_markers)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            return []
    return []


def _resolve_samples(raw_samples: Any) -> list[dict[str, Any]]:
    if raw_samples is None or (isinstance(raw_samples, float) and np.isnan(raw_samples)):
        return []
    if isinstance(raw_samples, list):
        return raw_samples
    if isinstance(raw_samples, str):
        try:
            parsed = json.loads(raw_samples)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            return []
    return []


def _marker_timestamp(markers: list[dict[str, Any]], marker_type: str) -> float | None:
    for marker in markers:
        if marker.get("type") == marker_type:
            try:
                return float(marker.get("timestamp"))
            except (TypeError, ValueError):
                return None
    return None


def _tempo_metrics(markers: list[dict[str, Any]]) -> tuple[float | None, float | None, float | None]:
    start = _marker_timestamp(markers, "start")
    impact = _marker_timestamp(markers, "impact")
    follow = _marker_timestamp(markers, "followThrough")

    time_to_impact = None
    follow_through = None
    ratio = None

    if start is not None and impact is not None and impact > start:
        time_to_impact = impact - start
    if impact is not None and follow is not None and follow > impact:
        follow_through = follow - impact
    if time_to_impact is not None and follow_through is not None and follow_through > 0:
        ratio = time_to_impact / follow_through

    return time_to_impact, follow_through, ratio


def extract_features(record: dict[str, Any]) -> dict[str, Any]:
    record = trim_record(record)
    swing_id = record.get("id")
    date = record.get("date")
    rating = record.get("rating")
    club = record.get("club")
    notes = record.get("notes")

    samples = _resolve_samples(record.get("samples"))
    markers = _resolve_event_markers(record.get("eventMarkers"))

    frame = pd.DataFrame(samples)
    required = ["timestamp", "accelX", "accelY", "accelZ", "gyroX", "gyroY", "gyroZ", "pitch", "roll", "yaw"]
    for col in required:
        if col not in frame.columns:
            frame[col] = np.nan

    frame = frame.sort_values("timestamp").reset_index(drop=True)

    accel_mag = np.sqrt(frame["accelX"] ** 2 + frame["accelY"] ** 2 + frame["accelZ"] ** 2)
    gyro_mag = np.sqrt(frame["gyroX"] ** 2 + frame["gyroY"] ** 2 + frame["gyroZ"] ** 2)

    orientation_std = frame[["pitch", "roll", "yaw"]].std(ddof=0).mean()
    swing_plane_stability = 1.0 / (1.0 + float(orientation_std if pd.notna(orientation_std) else 0.0))

    time_to_impact_seconds, follow_through_seconds, tempo_ratio = _tempo_metrics(markers)

    if len(frame) > 0:
        duration_seconds = float(frame["timestamp"].iloc[-1] - frame["timestamp"].iloc[0])
    else:
        duration_seconds = 0.0

    return {
        "id": swing_id,
        "date": date,
        "rating": rating,
        "club": club,
        "notes": notes,
        "sample_count": int(len(frame)),
        "duration_seconds": duration_seconds,
        "peak_accel_g": float(np.nanmax(accel_mag)) if len(accel_mag) else 0.0,
        "mean_accel_g": float(np.nanmean(accel_mag)) if len(accel_mag) else 0.0,
        "peak_rotational_velocity": float(np.nanmax(gyro_mag)) if len(gyro_mag) else 0.0,
        "mean_rotational_velocity": float(np.nanmean(gyro_mag)) if len(gyro_mag) else 0.0,
        "swing_plane_stability": swing_plane_stability,
        "time_to_impact_seconds": time_to_impact_seconds,
        "follow_through_seconds": follow_through_seconds,
        "tempo_ratio": tempo_ratio,
    }


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    records = load_records(input_path)
    features = [extract_features(record) for record in records]

    features_df = pd.DataFrame(features)
    csv_path = output_dir / "swing_features.csv"
    parquet_path = output_dir / "swing_features.parquet"
    features_df.to_csv(csv_path, index=False)
    features_df.to_parquet(parquet_path, index=False)

    print(f"Loaded {len(records)} records from {input_path}")
    print(f"Wrote feature table: {csv_path}")
    print(f"Wrote feature table: {parquet_path}")


if __name__ == "__main__":
    main()
