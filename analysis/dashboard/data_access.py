from __future__ import annotations

from pathlib import Path

import pandas as pd

DEFAULT_FEATURES_PATH = Path("analysis/output/swing_features.parquet")
FALLBACK_CSV_PATH = Path("analysis/output/swing_features.csv")


def _load_frame(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported file type: {suffix}")


def load_features(path_override: str | None = None) -> pd.DataFrame:
    """Load swing features table from parquet/csv output."""
    if path_override:
        frame = _load_frame(Path(path_override))
    elif DEFAULT_FEATURES_PATH.exists():
        frame = _load_frame(DEFAULT_FEATURES_PATH)
    elif FALLBACK_CSV_PATH.exists():
        frame = _load_frame(FALLBACK_CSV_PATH)
    else:
        raise FileNotFoundError(
            "No feature table found. Generate it with analysis/analyze_swings.py first."
        )

    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame["date_only"] = frame["date"].dt.date

    numeric_columns = [
        "rating",
        "sample_count",
        "duration_seconds",
        "peak_accel_g",
        "mean_accel_g",
        "peak_rotational_velocity",
        "mean_rotational_velocity",
        "swing_plane_stability",
        "time_to_impact_seconds",
        "follow_through_seconds",
        "tempo_ratio",
    ]
    for col in numeric_columns:
        if col in frame.columns:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")

    return frame

