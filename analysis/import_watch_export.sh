#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: analysis/import_watch_export.sh [--latest] [<golf_swings_export.json>] [--delete-raw]"
  echo ""
  echo "  --latest   Import the newest golf_swings_export*.json from ~/Downloads"
  echo "  --delete-raw  Remove data/raw/swings.json after features are generated"
  exit 1
}

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
INPUT_PATH=""
DELETE_RAW=false
USE_LATEST=false

for arg in "$@"; do
  case "$arg" in
    --delete-raw)
      DELETE_RAW=true
      ;;
    --latest)
      USE_LATEST=true
      ;;
    -h|--help)
      usage
      ;;
    *)
      if [[ -z "$INPUT_PATH" ]]; then
        INPUT_PATH="$(cd "$(dirname "$arg")" && pwd)/$(basename "$arg")"
      fi
      ;;
  esac
done

find_newest_export() {
  local dir="$1"
  if [[ ! -d "$dir" ]]; then
    return 1
  fi
  local newest=""
  local newest_mtime=0
  local file mtime
  while IFS= read -r -d '' file; do
    mtime="$(stat -f '%m' "$file")"
    if (( mtime > newest_mtime )); then
      newest_mtime=$mtime
      newest=$file
    fi
  done < <(find "$dir" -maxdepth 1 -name 'golf_swings_export*.json' -print0 2>/dev/null)
  if [[ -n "$newest" ]]; then
    printf '%s' "$newest"
  fi
}

warn_if_stale_export() {
  local chosen="$1"
  local dir
  dir="$(dirname "$chosen")"
  local newest
  newest="$(find_newest_export "$dir")"
  if [[ -n "$newest" && "$newest" != "$chosen" ]]; then
    echo "WARNING: A newer export exists in $dir:" >&2
    echo "  chosen:  $chosen" >&2
    echo "  newest:  $newest" >&2
    echo "  Re-run with --latest or pass the newest file path." >&2
    echo "" >&2
  fi
}

if [[ "$USE_LATEST" == "true" ]]; then
  INPUT_PATH="$(find_newest_export "$HOME/Downloads")"
  if [[ -z "$INPUT_PATH" ]]; then
    echo "No golf_swings_export*.json found in ~/Downloads." >&2
    exit 1
  fi
  echo "Using newest export: $INPUT_PATH"
elif [[ -z "$INPUT_PATH" ]]; then
  usage
fi

if [[ ! -f "$INPUT_PATH" ]]; then
  echo "Export file not found: $INPUT_PATH" >&2
  newest="$(find_newest_export "$HOME/Downloads")"
  if [[ -n "$newest" ]]; then
    echo "Try: analysis/import_watch_export.sh --latest" >&2
    echo "  or: analysis/import_watch_export.sh \"$newest\"" >&2
  fi
  exit 1
fi

warn_if_stale_export "$INPUT_PATH"

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
