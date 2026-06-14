# Data Pipeline: Watch → iPhone → Mac → Dashboard

End-to-end guide for moving captured swing data from the Apple Watch into the browser analytics dashboard.

## Overview

```mermaid
flowchart LR
  watchCapture[Watch captures motion] --> watchStore[Watch SwiftData store]
  watchStore --> wcSync[WatchConnectivity file transfer]
  wcSync --> phoneStore[iPhone SwiftData store]
  phoneStore --> phoneExport[iPhone Export / Share]
  phoneExport --> macRaw[data/raw/swings.json]
  macRaw --> featureGen[analyze_swings.py]
  featureGen --> macFeatures[analysis/output/swing_features.parquet]
  macRaw --> dashboardUI[Browser dashboard]
  macFeatures --> dashboardUI
```

| Stage | Device | What happens |
|-------|--------|--------------|
| 1. Capture | Watch | Motion samples saved as `SwingRecord` |
| 2. Sync | Watch → iPhone | JSON export transferred via WatchConnectivity |
| 3. Export | iPhone → Mac | Share/AirDrop `golf_swings_export.json` |
| 4. Import | Mac | Copy to `data/raw/` and generate feature files |
| 5. Analyze | Mac browser | Dashboard reads features + raw samples |

---

## Prerequisites

- **Paired devices:** Apple Watch and iPhone running the GolfSwingWatch apps
- **Same Wi‑Fi network:** Mac, iPhone, and Watch must be on the same network for watch deploy/sync
- **iPhone app opened once:** Initializes WatchConnectivity on the phone
- **Python venv** (for import/analysis):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r analysis/requirements.txt
```

- **Dashboard running** (Docker or local). See [analysis/web/README.md](analysis/web/README.md).

---

## Step 1: Record swings on the Watch

For **each swing**, use this sequence:

1. Tap **Start** — sample counter resets and begins climbing
2. Perform the swing
3. Tap **Stop** — counter stops increasing
4. Set **Rating**, **Club**, and **Notes** (optional)
5. Tap **Save Swing** — swing is stored on the watch

After save:
- Sample counter returns to **0**
- State returns to **Idle**
- Tap **Start** again before the next swing

> **Important:** Do not tap **Save** twice without a new **Start → Stop** cycle. That creates duplicate records with the same sensor data.

Each saved swing includes:
- Metadata: `id`, `date`, `rating`, `club`, `notes`
- Raw samples: accel, gyro, pitch, roll, yaw at ~50 Hz
- Event markers: `start`, `impact`, `followThrough` (when detected)
- Analytics and coaching recommendations

---

## Step 2: Transfer swings to the iPhone

There are two ways to get data onto the phone.

### Option A: Automatic sync on save

Each time you tap **Save Swing**, the watch queues a sync of that swing to the iPhone. If **Remove after iPhone sync** is enabled on the watch (default), those swings are deleted from the watch after the iPhone confirms they were saved.

### Option B: Send All to iPhone (manual batch)

1. Scroll down on the watch app
2. Confirm **Saved swings** count is greater than 0
3. Tap **Send All to iPhone**
4. Watch the status line below the button:
   - `Preparing...` / `Sending...` — export in progress
   - `Queued N swing(s) for iPhone` — file transfer started
   - `Sent to iPhone` — transfer completed
   - Error messages explain what went wrong (e.g. iPhone app not installed)

**Tips if sync fails:**
- Open the **iPhone app** at least once
- Keep iPhone unlocked and nearby
- Ensure Mac, iPhone, and Watch are on the **same Wi‑Fi network**

### Verify on iPhone

1. Open the **GolfSwingWatch** iPhone app
2. Go to **Sessions**
3. Check the **Watch Sync** section — status should show imported swings
4. Swings appear in the session list with club, date, rating, and sample count

---

## Step 3: Export from iPhone to Mac

The dashboard on your Mac does not read the iPhone directly. Export a JSON file first.

1. Open the iPhone app **Sessions** screen
2. Tap **Export** (top left)
3. Tap **Share** (top right) when it appears
4. Choose **AirDrop** to your Mac (or save to Files/iCloud and copy later)

The file is named `golf_swings_export.json`. It contains all swings currently stored on the iPhone, including full sensor samples.

---

## Step 4: Import on Mac

From the **repo root** (`GolfSwingWatch/`):

```bash
analysis/import_watch_export.sh ~/Downloads/golf_swings_export.json
```

Add `--delete-raw` to remove `data/raw/swings.json` after features are generated. Feature files in `analysis/output/` are kept.

Replace the path with wherever AirDrop saved the file.

### What the import script does

1. Copies the export to `data/raw/swings.json`
2. Trims idle noise before/after the swing using accel + gyro magnitude thresholds
3. Runs `analysis/analyze_swings.py` to build feature tables
4. Optionally removes the raw JSON with `--delete-raw`

```bash
analysis/import_watch_export.sh ~/Downloads/golf_swings_export.json --delete-raw
```

### Deleting stored swings

| Location | When | How |
|----------|------|-----|
| **Watch** | After iPhone confirms import (optional, on by default) | Toggle **Remove after iPhone sync** |
| **Watch** | Any time | Trash button on saved swing row |
| **iPhone** | On demand | Swipe left on session, or **Delete Swing** in detail view |
| **Mac analysis** | On demand | Re-import with `--delete-raw`, or delete `data/raw/swings.json` manually |
3. Writes:
   - `analysis/output/swing_features.parquet`
   - `analysis/output/swing_features.csv`

### Keep multiple sessions (optional)

Save dated copies before importing:

```bash
cp ~/Downloads/golf_swings_export.json data/raw/swings_2026-06-13.json
analysis/import_watch_export.sh data/raw/swings_2026-06-13.json
```

Only `data/raw/swings.json` is used by default for Movement Explorer. The import script overwrites it each run.

---

## Step 5: View the dashboard

### Start the dashboard (Docker)

```bash
cp analysis/web/.env.example analysis/web/.env   # first time only
docker compose -f analysis/web/docker-compose.yml --env-file analysis/web/.env up --build
```

Open **http://localhost:5173**

### What the dashboard shows

| Section | Data source | Content |
|---------|-------------|---------|
| KPIs, charts, table | `analysis/output/swing_features.parquet` | Per-swing metrics (tempo, peak rotation, etc.) |
| Movement Explorer | `data/raw/swings.json` | Raw time-series + 3D watch-face visualizer |

After importing new swings, **refresh the browser**.

### Generate features manually (without import script)

```bash
source .venv/bin/activate
python analysis/analyze_swings.py \
  --input data/raw/swings.json \
  --output-dir analysis/output
```

---

## File layout reference

```text
GolfSwingWatch/
  data/
    raw/
      swings.json              # latest raw export (Movement Explorer reads this)
  analysis/
    output/
      swing_features.parquet   # feature table (dashboard KPIs/charts)
      swing_features.csv       # same data in CSV form
    import_watch_export.sh     # one-command import helper
    analyze_swings.py          # feature extraction CLI
    web/                       # Docker compose + web stack docs
```

---

## Quick reference checklist

```text
[ ] Watch: Start → swing → Stop → Save (repeat per swing)
[ ] Watch: Send All to iPhone (or rely on per-save sync)
[ ] iPhone: Confirm swings in Sessions / Watch Sync
[ ] iPhone: Export → Share → AirDrop to Mac
[ ] Mac:  analysis/import_watch_export.sh <path-to-json>
[ ] Mac:  Refresh http://localhost:5173
```

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|--------------|-----|
| Send All to iPhone unresponsive | Large export blocking UI | Rebuild watch app (recent fix); watch status line for errors |
| Sync not ready | iPhone app never opened | Launch iPhone app once |
| Swings not on iPhone | WatchConnectivity tunnel | Same Wi‑Fi on Mac/iPhone/Watch; keep devices unlocked |
| Dashboard 404 / empty | No feature files yet | Run import script or `analyze_swings.py` |
| Movement Explorer empty | No raw JSON | Confirm `data/raw/swings.json` exists after import |
| Duplicate swings, same data | Saved without new capture | Use full Start → Stop → Save cycle each time |

---

## Related docs

- [analysis/README.md](analysis/README.md) — feature extraction and metrics
- [analysis/web/README.md](analysis/web/README.md) — dashboard setup, Docker, API
- [DATA_MODEL.md](DATA_MODEL.md) — `SwingRecord` schema
