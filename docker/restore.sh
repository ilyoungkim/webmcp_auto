#!/usr/bin/env bash
# ============================================================================
# WebMCP Auto — Docker 복원 스크립트
# ============================================================================
# backup.sh 로 만든 백업에서 PostgreSQL 데이터 + 설정 파일을 복원합니다.
#
# 사용법:
#   ./restore.sh                          # 최신 백업 자동 선택
#   ./restore.sh <백업폴더경로>            # 특정 백업 지정
#   ./restore.sh --list                   # 백업 목록 보기
#
# 주의:
#   - 현재 DB 데이터는 덮어써집니다. (복원 전 현재 DB 백업 권장)
#   - .env 는 복원하지 않습니다. (시크릿은 기존 유지)
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_ROOT="${BACKUP_ROOT:-$SCRIPT_DIR/backups}"

# ── --list: 백업 목록 ─────────────────────────────────────────
if [ "${1:-}" = "--list" ]; then
  echo "📂 백업 목록:"
  ls -1dt "$BACKUP_ROOT"/webmcp_backup_* 2>/dev/null | while read -r d; do
    echo "  $(basename "$d")  ($(du -sh "$d" 2>/dev/null | cut -f1))"
  done || echo "  백업이 없습니다."
  exit 0
fi

# ── 백업 폴더 결정 ─────────────────────────────────────────────
if [ -n "${1:-}" ] && [ -d "$1" ]; then
  BACKUP_DIR="$1"
else
  # 최신 백업 자동 선택
  BACKUP_DIR="$(ls -1dt "$BACKUP_ROOT"/webmcp_backup_* 2>/dev/null | head -1 || true)"
  if [ -z "$BACKUP_DIR" ]; then
    echo "❌ 백업이 없습니다. 먼저 ./backup.sh 를 실행하세요." >&2
    exit 1
  fi
fi

DUMP="$BACKUP_DIR/postgres_dump.sql"
if [ ! -f "$DUMP" ]; then
  echo "❌ $DUMP 파일이 없습니다." >&2
  exit 1
fi

echo "📂 복원 대상: $BACKUP_DIR"

# ── postgres 컨테이너 확인 ────────────────────────────────────
if ! docker compose ps postgres >/dev/null 2>&1 || ! docker compose exec -T postgres pg_isready -U webmcp -d webmcp >/dev/null 2>&1; then
  echo "❌ postgres 컨테이너가 실행 중이 아닙니다. 먼저 docker compose up -d 를 실행하세요." >&2
  exit 1
fi

# ── 확인 ───────────────────────────────────────────────────────
echo ""
echo "⚠️  현재 DB 데이터가 백업 내용으로 덮어써집니다."
read -r -p "계속하시겠습니까? (y/N): " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
  echo "취소되었습니다."
  exit 0
fi

# ── 복원 ───────────────────────────────────────────────────────
echo "🗄️  PostgreSQL 복원 중..."
docker compose exec -T postgres psql -U webmcp -d webmcp < "$DUMP"
echo "   ✅ DB 복원 완료"

echo ""
echo "✅ 복원 완료: $BACKUP_DIR"
echo "   (설정 파일은 docker/ 폴더에 이미 있으므로 별도 복원 불필요)"
