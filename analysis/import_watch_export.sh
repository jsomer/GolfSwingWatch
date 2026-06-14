#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: analysis/import_watch_export.sh <golf_swings_export.json> [--delete-raw]"
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
INPUT_PATH=""
DELETE_RAW=false

for arg in "$@"; do
  case "$arg" in
    --delete-raw)
      DELETE_RAW=true
      ;;
    *)
      if [[ -z "$INPUT_PATH" ]]; then
        INPUT_PATH="$(cd "$(dirname "$arg")" && pwd)/$(basename "$arg")"
      fi
      ;;
  esac
done

if [[ -z "$INPUT_PATH" ]]; then
  echo "Usage: analysis/import_watch_export.sh <golf_swings_export.json> [--delete-raw]"
  exit 1
fi

mkdir -p "$ROOT_DIR/data/raw" "$ROOT_DIR/analysis/output"
cp "$INPUT_PATH" "$ROOT_DIR/data/raw/swings.json"

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON="$ROOT_DIR/.venv/bin/python"
else
  PYTHON="python3"
fi

cd "$ROOT_DIR"
"$PYTHON" - <<'PY'
from pathlib import Path
from analysis.swing_trim import trim_json_file

trim_json_file(Path("data/raw/swings.json"))
print("Trimmed leading/trailing noise from swing samples.")
PY

"$PYTHON" "$ROOT_DIR/analysis/analyze_swings.py" \
  --input "$ROOT_DIR/data/raw/swings.json" \
  --output-dir "$ROOT_DIR/analysis/output"

if [[ "$DELETE_RAW" == "true" ]]; then
  rm -f "$ROOT_DIR/data/raw/swings.json"
  echo "Removed data/raw/swings.json after import."
fi

echo "Imported swings into analysis/output."
echo "Refresh the dashboard at http://localhost:5173"
