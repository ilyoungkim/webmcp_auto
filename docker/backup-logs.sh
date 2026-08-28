#!/usr/bin/env bash
# ============================================================================
# WebMCP Auto - Container Log Backup Script
# ============================================================================
# Backs up logs from all containers (backend/worker/frontend/nginx/postgres).
# Backups are retained for 28 days (4 weeks) by default, then auto-deleted.
#
# Usage:
#   ./backup-logs.sh                  # default: docker/backups/logs/
#   ./backup-logs.sh /path/to/dir     # custom path
#   ./backup-logs.sh --tail 500       # only last 500 lines
#   ./backup-logs.sh --retention 28   # retention days (default 28 = 4 weeks)
#
# Output:
#   <target>/logs_YYYYMMDD_HHMMSS/
#     backend.log  worker.log  frontend.log  nginx.log  postgres.log
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_ROOT="$SCRIPT_DIR/backups/logs"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$BACKUP_ROOT/logs_$STAMP"
TAIL_LINES=""
RETENTION_DAYS=28

# --- parse args ------------------------------------------------------------
while [ $# -gt 0 ]; do
  case "$1" in
    --tail)
      TAIL_LINES="${2:-}"
      shift 2
      ;;
    --retention)
      RETENTION_DAYS="${2:-28}"
      shift 2
      ;;
    *)
      BACKUP_ROOT="$1"
      shift
      ;;
  esac
done

# --- create backup dir -----------------------------------------------------
mkdir -p "$BACKUP_DIR"
echo "Backup dir: $BACKUP_DIR"

# --- backup each container log ---------------------------------------------
CONTAINERS=(webmcp-backend webmcp-worker webmcp-frontend webmcp-nginx webmcp-postgres)
COUNT=0

for c in "${CONTAINERS[@]}"; do
  if docker ps --format "{{.Names}}" | grep -q "^$c$"; then
    LOGFILE="$BACKUP_DIR/$c.log"
    if [ -n "$TAIL_LINES" ]; then
      docker logs --tail "$TAIL_LINES" "$c" > "$LOGFILE" 2>&1
    else
      docker logs "$c" > "$LOGFILE" 2>&1
    fi
    SIZE=$(wc -c < "$LOGFILE" | tr -d ' ')
    echo "  OK $c.log ($SIZE bytes)"
    COUNT=$((COUNT + 1))
  else
    echo "  SKIP $c (not running)"
  fi
done

if [ "$COUNT" -eq 0 ]; then
  echo "ERROR: no logs backed up. Check containers are running." >&2
  exit 1
fi

echo ""
echo "DONE: log backup complete -> $BACKUP_DIR ($COUNT containers)"

# --- retention cleanup (default 28 days = 4 weeks) -------------------------
if [ "$RETENTION_DAYS" -gt 0 ]; then
  echo ""
  echo "Cleaning log backups older than $RETENTION_DAYS days..."
  CUTOFF=$(date -v-${RETENTION_DAYS}d +%Y%m%d 2>/dev/null || date -d "-${RETENTION_DAYS} days" +%Y%m%d)
  DELETED=0
  for d in "$BACKUP_ROOT"/logs_*; do
    [ -d "$d" ] || continue
    name=$(basename "$d")
    date_part="${name#logs_}"
    date_part="${date_part:0:8}"
    if [[ "$date_part" =~ ^[0-9]{8}$ ]] && [ "$date_part" -lt "$CUTOFF" ]; then
      rm -rf "$d"
      echo "  Deleted: $name"
      DELETED=$((DELETED + 1))
    fi
  done
  echo "  Cleanup done ($DELETED deleted)"
fi
