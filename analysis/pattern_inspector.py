"""Cohort pattern analysis over swing feature tables (Pattern Inspector v1)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from analysis.pattern_inspector_llm import attach_llm_narrative
except ImportError:
    from pattern_inspector_llm import attach_llm_narrative

FAULT_LABELS: dict[str, str] = {
    "rushed_transition": "Rushed transition",
    "excessive_wrist_roll": "Excessive wrist roll",
    "mid_swing_pause": "Mid-swing pause",
    "incomplete_finish": "Incomplete finish",
}

METRIC_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("tempo_ratio", "Tempo (backswing / downswing)", "lower in rushed swings"),
    ("backswing_duration_seconds", "Backswing duration", "seconds"),
    ("downswing_duration_seconds", "Downswing duration", "seconds"),
    ("follow_through_rotation_deg", "Wrist return rotation", "degrees"),
    ("swing_plane_stability", "Swing plane stability", "0–1 scale"),
    ("peak_rotational_velocity", "Peak rotation speed", "rad/s"),
    ("duration_seconds", "Clip duration", "seconds"),
)

DEFAULT_LOW_RATING = 2
DEFAULT_HIGH_RATING = 4
MIN_COHORT_SIZE = 2
FAULT_PREVALENCE_THRESHOLD = 0.5


def _parse_fault_flags(raw: Any) -> list[str]:
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return []
    if isinstance(raw, list):
        return [str(item) for item in raw if str(item).strip()]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(item) for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            stripped = raw.strip()
            return [stripped] if stripped else []
    return []


def _cohort(frame: pd.DataFrame, low_threshold: int, high_threshold: int) -> dict[str, pd.DataFrame]:
    if "rating" not in frame.columns:
        return {"all": frame, "low": frame.iloc[0:0], "high": frame.iloc[0:0]}
    ratings = pd.to_numeric(frame["rating"], errors="coerce")
    return {
        "all": frame,
        "low": frame[ratings <= low_threshold].copy(),
        "high": frame[ratings >= high_threshold].copy(),
    }


def _metric_summary(frame: pd.DataFrame) -> dict[str, float | None]:
    summary: dict[str, float | None] = {}
    for column, _, _ in METRIC_COLUMNS:
        if column not in frame.columns:
            continue
        values = pd.to_numeric(frame[column], errors="coerce").dropna()
        if values.empty:
            summary[column] = None
        else:
            summary[column] = float(values.mean())
    return summary


def _fault_prevalence(frame: pd.DataFrame) -> dict[str, float]:
    if frame.empty or "fault_flags" not in frame.columns:
        return {}
    counts: dict[str, int] = {}
    total = len(frame)
    for raw in frame["fault_flags"]:
        for flag in _parse_fault_flags(raw):
            counts[flag] = counts.get(flag, 0) + 1
    return {flag: count / total for flag, count in counts.items()}


def _swing_brief(row: pd.Series) -> dict[str, Any]:
    return {
        "id": str(row.get("id", "")),
        "date": str(row.get("date", "")),
        "club": str(row.get("club", "")),
        "rating": row.get("rating"),
        "tempo_ratio": row.get("tempo_ratio"),
        "fault_flags": _parse_fault_flags(row.get("fault_flags")),
    }


def _detect_patterns(
    low: pd.DataFrame,
    high: pd.DataFrame,
    *,
    min_cohort: int,
) -> list[dict[str, Any]]:
    patterns: list[dict[str, Any]] = []
    if len(low) < min_cohort:
        return patterns

    low_faults = _fault_prevalence(low)
    high_faults = _fault_prevalence(high) if len(high) >= min_cohort else {}

    for fault, low_rate in sorted(low_faults.items(), key=lambda item: item[1], reverse=True):
        high_rate = high_faults.get(fault, 0.0)
        if low_rate < FAULT_PREVALENCE_THRESHOLD:
            continue
        if len(high) >= min_cohort and high_rate >= low_rate * 0.75:
            continue
        label = FAULT_LABELS.get(fault, fault)
        affected = [
            _swing_brief(row)
            for _, row in low.iterrows()
            if fault in _parse_fault_flags(row.get("fault_flags"))
        ]
        patterns.append(
            {
                "kind": "fault",
                "fault": fault,
                "title": label,
                "summary": (
                    f"{label} appears in {low_rate:.0%} of low-rated swings"
                    + (
                        f" vs {high_rate:.0%} of high-rated swings"
                        if len(high) >= min_cohort
                        else ""
                    )
                    + "."
                ),
                "low_prevalence": low_rate,
                "high_prevalence": high_rate,
                "affected_swings": affected[:10],
            }
        )

    if len(high) >= min_cohort:
        low_metrics = _metric_summary(low)
        high_metrics = _metric_summary(high)
        for column, label, unit in METRIC_COLUMNS:
            low_value = low_metrics.get(column)
            high_value = high_metrics.get(column)
            if low_value is None or high_value is None or high_value == 0:
                continue
            delta_ratio = (low_value - high_value) / abs(high_value)
            if abs(delta_ratio) < 0.2:
                continue
            direction = "higher" if low_value > high_value else "lower"
            patterns.append(
                {
                    "kind": "metric",
                    "metric": column,
                    "title": f"{label} is {direction} in low-rated swings",
                    "summary": (
                        f"Low-rated average {label.lower()}: {low_value:.2f} {unit}; "
                        f"high-rated average: {high_value:.2f} {unit} "
                        f"({delta_ratio:+.0%} difference)."
                    ),
                    "low_average": low_value,
                    "high_average": high_value,
                    "delta_ratio": delta_ratio,
                }
            )

    return patterns


def _practice_stats(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty or "swing_mode" not in frame.columns:
        return {"practice_count": 0, "full_count": 0, "practice_pct": None}
    modes = frame["swing_mode"].astype(str).str.lower()
    practice_count = int((modes == "practice").sum())
    full_count = int((modes == "full").sum())
    total = practice_count + full_count
    practice_pct = practice_count / total if total else None
    return {
        "practice_count": practice_count,
        "full_count": full_count,
        "practice_pct": practice_pct,
    }


def _phase_chain_stats(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty or "phase_chain_complete" not in frame.columns:
        return {"complete_count": 0, "complete_pct": None}
    complete = frame["phase_chain_complete"]
    if complete.dtype == object:
        complete = complete.astype(str).str.lower().isin({"true", "1", "yes"})
    complete_count = int(complete.sum())
    return {
        "complete_count": complete_count,
        "complete_pct": complete_count / len(frame) if len(frame) else None,
    }


def inspect_patterns(
    frame: pd.DataFrame,
    *,
    low_rating_threshold: int = DEFAULT_LOW_RATING,
    high_rating_threshold: int = DEFAULT_HIGH_RATING,
    min_cohort_size: int = MIN_COHORT_SIZE,
    include_llm: bool = False,
) -> dict[str, Any]:
    """Analyze feature table and return structured pattern report."""
    working = frame.copy()
    if "fault_flags" not in working.columns:
        working["fault_flags"] = [[] for _ in range(len(working))]

    cohorts = _cohort(working, low_rating_threshold, high_rating_threshold)
    low = cohorts["low"]
    high = cohorts["high"]

    patterns = _detect_patterns(low, high, min_cohort=min_cohort_size)

    report = {
        "analysis_version": "pattern_inspector_v1",
        "swing_count": int(len(working)),
        "low_rated_count": int(len(low)),
        "high_rated_count": int(len(high)),
        "low_rating_threshold": low_rating_threshold,
        "high_rating_threshold": high_rating_threshold,
        "practice": _practice_stats(working),
        "phase_chain": _phase_chain_stats(working),
        "low_rated_faults": _fault_prevalence(low),
        "high_rated_faults": _fault_prevalence(high),
        "low_rated_metrics": _metric_summary(low),
        "high_rated_metrics": _metric_summary(high),
        "patterns": patterns,
    }
    report["markdown"] = render_markdown(report)
    return attach_llm_narrative(report, enabled=include_llm)


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Swing Pattern Report",
        "",
        f"- **Swings analyzed:** {report['swing_count']}",
        f"- **Low-rated (≤{report['low_rating_threshold']}):** {report['low_rated_count']}",
        f"- **High-rated (≥{report['high_rating_threshold']}):** {report['high_rated_count']}",
    ]

    practice = report.get("practice", {})
    if practice.get("practice_pct") is not None:
        lines.append(
            f"- **Practice mode:** {practice['practice_count']} swings "
            f"({practice['practice_pct']:.0%} without confident contact)"
        )

    phase = report.get("phase_chain", {})
    if phase.get("complete_pct") is not None:
        lines.append(
            f"- **Full phase chain detected:** {phase['complete_count']} swings "
            f"({phase['complete_pct']:.0%})"
        )

    lines.extend(["", "## Key patterns", ""])
    patterns = report.get("patterns", [])
    if not patterns:
        lines.append(
            "_No strong cohort patterns yet. Record more swings with varied ratings, "
            "or confirm flaw tags on iPhone._"
        )
    else:
        for index, pattern in enumerate(patterns, start=1):
            lines.append(f"{index}. **{pattern['title']}** — {pattern['summary']}")
            affected = pattern.get("affected_swings") or []
            if affected:
                examples = ", ".join(
                    f"{item.get('club', '?')} ({item.get('date', '')[:10]})"
                    for item in affected[:5]
                )
                lines.append(f"   - Examples: {examples}")

    lines.extend(["", "## Fault prevalence (low-rated)", ""])
    low_faults = report.get("low_rated_faults") or {}
    if not low_faults:
        lines.append("_None detected._")
    else:
        for fault, rate in sorted(low_faults.items(), key=lambda item: item[1], reverse=True):
            label = FAULT_LABELS.get(fault, fault)
            lines.append(f"- {label}: {rate:.0%}")

    return "\n".join(lines) + "\n"


def load_feature_frame(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported feature file: {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect swing cohort patterns.")
    parser.add_argument(
        "--features",
        default="analysis/output/swing_features.parquet",
        help="Path to swing_features.parquet or .csv",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional path to write markdown report",
    )
    parser.add_argument("--low-rating", type=int, default=DEFAULT_LOW_RATING)
    parser.add_argument("--high-rating", type=int, default=DEFAULT_HIGH_RATING)
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Request an OpenAI narrative summary (requires OPENAI_API_KEY)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frame = load_feature_frame(Path(args.features))
    report = inspect_patterns(
        frame,
        low_rating_threshold=args.low_rating,
        high_rating_threshold=args.high_rating,
        include_llm=args.llm,
    )
    markdown = report["markdown"]
    if report.get("llm_narrative"):
        markdown = f"{markdown}\n## AI Summary\n\n{report['llm_narrative']}\n"
    elif report.get("llm_error"):
        print(f"LLM summary skipped: {report['llm_error']}", flush=True)
    if args.output:
        Path(args.output).write_text(markdown, encoding="utf-8")
        print(f"Wrote pattern report: {args.output}")
    else:
        print(markdown)


if __name__ == "__main__":
    main()
