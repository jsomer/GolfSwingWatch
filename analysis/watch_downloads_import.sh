#!/usr/bin/env bash
# Watch ~/Downloads for new golf_swings_export*.json and run import_watch_export.sh --latest.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
IMPORT_SCRIPT="$ROOT_DIR/analysis/import_watch_export.sh"
DOWNLOADS_DIR="${HOME}/Downloads"
POLL_SECONDS=5
SETTLE_SECONDS=2
DELETE_RAW=false
RUN_ONCE=false

usage() {
  cat <<'EOF'
Usage: analysis/watch_downloads_import.sh [options]

Watches a folder for golf swing exports and imports the newest file automatically.

Options:
  --downloads-dir PATH   Folder to watch (default: ~/Downloads)
  --poll-seconds N       Poll interval when fswatch is unavailable (default: 5)
  --settle-seconds N     Wait for file writes to finish before import (default: 2)
  --delete-raw           Pass --delete-raw to import_watch_export.sh
  --once                 Import the newest export now and exit
  --help                 Show this help

Requires fswatch for instant detection (brew install fswatch), otherwise polls.

Leave this running in a terminal while you AirDrop exports from the iPhone.
Refresh http://localhost:5173 after each import.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --downloads-dir)
      shift
      DOWNLOADS_DIR="${1:?missing path after --downloads-dir}"
      ;;
    --poll-seconds)
      shift
      POLL_SECONDS="${1:?missing value after --poll-seconds}"
      ;;
    --settle-seconds)
      shift
      SETTLE_SECONDS="${1:?missing value after --settle-seconds}"
      ;;
    --delete-raw)
      DELETE_RAW=true
      ;;
    --once)
      RUN_ONCE=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
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

export_mtime() {
  local file="$1"
  stat -f '%m' "$file"
}

LAST_IMPORTED_PATH=""
LAST_IMPORTED_MTIME=0

run_import() {
  local import_args=(--latest)
  if [[ "$DELETE_RAW" == "true" ]]; then
    import_args+=(--delete-raw)
  fi

  echo ""
  echo "[$(date '+%H:%M:%S')] Importing newest export from $DOWNLOADS_DIR ..."
  if bash "$IMPORT_SCRIPT" "${import_args[@]}"; then
    local newest
    newest="$(find_newest_export "$DOWNLOADS_DIR")"
    if [[ -n "$newest" ]]; then
      LAST_IMPORTED_PATH="$newest"
      LAST_IMPORTED_MTIME="$(export_mtime "$newest")"
    fi
    echo "[$(date '+%H:%M:%S')] Done. Refresh http://localhost:5173"
  else
    echo "[$(date '+%H:%M:%S')] Import failed." >&2
  fi
  echo ""
}

should_import() {
  local candidate
  candidate="$(find_newest_export "$DOWNLOADS_DIR")"
  if [[ -z "$candidate" ]]; then
    return 1
  fi

  local mtime
  mtime="$(export_mtime "$candidate")"
  if [[ "$candidate" == "$LAST_IMPORTED_PATH" && "$mtime" == "$LAST_IMPORTED_MTIME" ]]; then
    return 1
  fi
  return 0
}

wait_for_stable_file() {
  local file="$1"
  local previous=-1
  local stable=0
  while (( stable < SETTLE_SECONDS )); do
    sleep 1
    local current
    current="$(export_mtime "$file")"
    if [[ "$current" == "$previous" ]]; then
      stable=$((stable + 1))
    else
      stable=0
      previous=$current
    fi
  done
}

handle_candidate() {
  local candidate
  candidate="$(find_newest_export "$DOWNLOADS_DIR")"
  if [[ -z "$candidate" ]]; then
    return 0
  fi
  wait_for_stable_file "$candidate"
  if should_import; then
    run_import
  fi
}

if [[ "$RUN_ONCE" == "true" ]]; then
  run_import
  exit 0
fi

if [[ ! -d "$DOWNLOADS_DIR" ]]; then
  echo "Downloads folder not found: $DOWNLOADS_DIR" >&2
  exit 1
fi

echo "GolfSwingWatch auto-import watcher"
echo "  folder:  $DOWNLOADS_DIR"
echo "  repo:    $ROOT_DIR"
echo "  pattern: golf_swings_export*.json"
echo ""
echo "AirDrop from iPhone, then refresh http://localhost:5173 after each import."
echo "Press Ctrl+C to stop."
echo ""

# Import anything already waiting.
if should_import; then
  run_import
fi

if command -v fswatch >/dev/null 2>&1; then
  echo "Using fswatch for file events."
  fswatch -0 -e '.*' -i 'golf_swings_export.*\.json$' "$DOWNLOADS_DIR" | while IFS= read -r -d '' _; do
    handle_candidate
  done
else
  echo "fswatch not found — polling every ${POLL_SECONDS}s (brew install fswatch for instant detection)."
  while true; do
    if should_import; then
      handle_candidate
    fi
    sleep "$POLL_SECONDS"
  done
fi
