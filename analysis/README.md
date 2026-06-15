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
analysis/import_watch_export.sh --latest
```

## Mac swing database

Imports **merge** into `data/raw/swings.json` by swing `id` — the Mac keeps all swings unless you delete them:

```bash
analysis/import_watch_export.sh --latest
python -m analysis.swing_store list
python -m analysis.swing_store stats
python -m analysis.swing_store delete --id <SWING_UUID> --rebuild
```

Each import is also archived under `data/exports/`. See **[DATA_PIPELINE.md](../DATA_PIPELINE.md)** for the full workflow.

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

## Pattern Inspector

Compare low-rated vs high-rated swing cohorts using fault flags and phase metrics:

```bash
source .venv/bin/activate
python analysis/pattern_inspector.py --features analysis/output/swing_features.parquet
python analysis/pattern_inspector.py --output analysis/output/pattern_report.md
```

Optional AI narrative (requires `OPENAI_API_KEY`):

```bash
python analysis/pattern_inspector.py --llm --output analysis/output/pattern_report.md
```

Patterns are strongest when you have swings rated ≤2 and ≥4. All-middle ratings produce an empty pattern list.

## Output files

- `analysis/output/swing_features.csv`
- `analysis/output/swing_features.parquet`
- `analysis/output/pattern_report.md` (optional, from `pattern_inspector.py`)

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
- `tempo_ratio` (backswing / downswing duration from phase detection; see `tempo_source`)
- `follow_through_rotation_deg` and related follow-through metrics (practice swings)
- `fault_flags`, `phase_chain_complete`, `swing_mode` (practice vs full)

## Next additions

- Session-level aggregations (consistency per day/week).
- ML rating classifier once enough labeled swings exist.
- Side-by-side swing comparisons in the dashboard.
