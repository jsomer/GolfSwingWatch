# Swing Analysis Pipeline

Starter local analytics pipeline for captured swing data.

## What it does

- Loads swing exports from JSON, JSONL, or Parquet.
- Trims leading/trailing low-activity noise before analysis (accel/gyro magnitude thresholds).
- Normalizes nested swing samples into a tabular format.
- Computes per-swing feature metrics from raw sensor signals.
- Writes a feature table for downstream dashboards and modeling.

## Expected input shape

The loader expects records matching `SwingRecord` from the app:

- `id`
- `date`
- `rating`
- `club`
- `notes`
- `samples` (array of `SwingSample`)
- `eventMarkers` (array of timestamp/type pairs, optional but recommended)

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r analysis/requirements.txt
python analysis/analyze_swings.py --input data/raw/swings.json --output-dir analysis/output
```

## Import swings from Apple Watch

See **[DATA_PIPELINE.md](../DATA_PIPELINE.md)** for the complete Watch → iPhone → Mac → dashboard guide.

Quick import after AirDrop:

```bash
analysis/import_watch_export.sh ~/Downloads/golf_swings_export.json
```

Add `--delete-raw` to remove the copied JSON from `data/raw/` after features are generated.

## Run regression tests

```bash
source .venv/bin/activate
pytest analysis/tests -q
```

## Browser dashboard

Run the interactive dashboard in your browser:

```bash
source .venv/bin/activate
streamlit run analysis/dashboard/app.py
```

The app loads `analysis/output/swing_features.parquet` by default (falls back to CSV).
Movement traces load from `data/raw/swings.json` (raw watch export with samples).
You can also enter a custom file path in the dashboard sidebar.

## Production-oriented web UI

For a split backend/frontend browser architecture, see:

- `analysis/web/README.md`

## Output files

- `analysis/output/swing_features.csv`
- `analysis/output/swing_features.parquet`

## Initial metrics

- `sample_count`
- `duration_seconds`
- `peak_accel_g`
- `mean_accel_g`
- `peak_rotational_velocity`
- `mean_rotational_velocity`
- `swing_plane_stability`
- `time_to_impact_seconds` (from markers)
- `follow_through_seconds` (from markers)
- `tempo_ratio` (`time_to_impact_seconds` / `follow_through_seconds`)

## Next additions

- Session-level aggregations (consistency per day/week).
- Filtering and smoothing options.
- Side-by-side comparisons by club and rating bands.
