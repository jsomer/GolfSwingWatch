# Web Analytics Stack

Production-oriented browser stack for swing analytics:

- `analysis/web_api`: FastAPI backend exposing filtered records and summary metrics.
- `analysis/web_ui`: React + Vite frontend for interactive browser dashboards.

## 1) Start backend API

From repo root:

```bash
source .venv/bin/activate
pip install -r analysis/web_api/requirements.txt
uvicorn analysis.web_api.main:app --reload --port 8000
```

Optional custom data path:

```bash
FEATURE_TABLE_PATH=analysis/output/swing_features.csv uvicorn analysis.web_api.main:app --reload --port 8000
```

The default app reads `analysis/output/swing_features.parquet` then CSV fallback.

### Security env vars

- `ALLOWED_ORIGINS`: comma-separated CORS allowlist.  
  Default: `http://localhost:5173,http://127.0.0.1:5173`
- `API_KEY`: if set, `GET /summary` and `GET /records` require header `X-API-Key`.

## 2) Start React frontend

In a second terminal:

```bash
cd analysis/web_ui
npm install
npm run dev
```

Set API base via `.env` if needed:

```bash
cp .env.example .env
```

If backend API key auth is enabled, set `VITE_API_KEY` in `.env`.

## 3) Run with Docker Compose

```bash
cp analysis/web/.env.example analysis/web/.env
docker compose -f analysis/web/docker-compose.yml --env-file analysis/web/.env up --build
```

Then open:

- UI: `http://localhost:5173`
- API health: `http://localhost:8000/health`

## Generate feature data (required before dashboard loads)

The API returns 404 on `/summary` and `/records` until feature files exist.

```bash
source .venv/bin/activate
mkdir -p analysis/output
python analysis/analyze_swings.py --input analysis/tests/fixtures/test_swings.json --output-dir analysis/output
```

For real swing exports from the watch app, see [DATA_PIPELINE.md](../../DATA_PIPELINE.md).

```bash
analysis/import_watch_export.sh ~/Downloads/golf_swings_export.json
```

Then refresh `http://localhost:5173`.

## Movement Explorer (Plotly)

Scroll to the bottom of the dashboard to open **Movement Explorer**. It loads raw swing exports from `data/raw/swings.json` and renders:

- a 3D watch-face visualizer with scrub/play controls
- acceleration magnitude over time
- rotational velocity magnitude over time
- pitch / roll / yaw orientation over time
- dashed vertical markers for `start`, `impact`, and `followThrough` events

## Restart and resume checklist

After a machine restart, use this exact sequence from repo root:

```bash
open -a "Docker"
docker version
mkdir -p analysis/output
test -f analysis/output/swing_features.parquet || python analysis/analyze_swings.py --input analysis/tests/fixtures/test_swings.json --output-dir analysis/output
test -f analysis/web/.env || cp analysis/web/.env.example analysis/web/.env
docker compose -f analysis/web/docker-compose.yml --env-file analysis/web/.env up --build
```

If `docker version` fails, Docker Desktop is not ready yet; wait until it shows as running and retry.

To stop services later:

```bash
docker compose -f analysis/web/docker-compose.yml --env-file analysis/web/.env down
```

## Docker troubleshooting on macOS

- **Env file missing**
  - Error: `couldn't find env file ... analysis/web/.env`
  - Fix: `cp analysis/web/.env.example analysis/web/.env`

- **Mounts denied / path not shared**
  - Error mentions `analysis/output` is not shared.
  - Fix in Docker Desktop: `Settings -> Resources -> File Sharing`
  - Add: `/Users/johnsomerville/SoftwareProjects` (or `/Users/johnsomerville`)
  - Apply and restart Docker Desktop, then rerun compose.

- **Daemon not reachable**
  - Errors like `Cannot connect to the Docker daemon`.
  - Fix: fully quit/reopen Docker Desktop, then run `docker version` again.

- **Dashboard shows 404 / failed to load summary**
  - UI and `/health` work, but `/summary` or `/records` return 404.
  - Cause: missing `analysis/output/swing_features.parquet` (or CSV).
  - Fix: run the feature generation command in **Generate feature data** above, then refresh the browser.
  - If API key auth is enabled, ensure `analysis/web/.env` has `API_KEY=change-me` and the UI was built with the same key.

## API endpoints

- `GET /health`
- `GET /summary` with optional query params: `clubs`, `ratings`, `start_date`, `end_date`
- `GET /records` with optional query params: `limit`, `clubs`, `ratings`, `start_date`, `end_date`
- `GET /movement/swings` list swings available in raw export JSON
- `GET /movement/{swing_id}` time-series sensor trace for Plotly movement charts

## Backend tests

```bash
source .venv/bin/activate
python -m pytest analysis/web_api/tests -q
```
