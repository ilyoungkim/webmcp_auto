#!/usr/bin/env bash
# ============================================================================
# WebMCP Auto — Docker 백업 스크립트
# ============================================================================
# ⭐ 가장 중요한 것은 PostgreSQL DB 데이터입니다.
#   - postgres_dump.sql : 운영 DB 전체 덤프 (사용자·프로젝트·Q&A·위젯·채팅 등)
#   - 설정 파일은 부차적 (git에 이미 있으므로 참고용)
#
# 사용법:
#   ./backup.sh                 # 기본 백업 (docker/backups/ 에 저장)
#   ./backup.sh /path/to/dir    # 지정 경로에 백업
#   ./backup.sh --db-only       # DB 덤프만 (설정 파일 제외)
#
# 생성물:
#   <대상>/webmcp_backup_YYYYMMDD_HHMMSS/
#     ├── postgres_dump.sql     # ⭐ 운영 DB 전체 덤프 (가장 중요)
#     ├── docker-compose.yml    # 설정 파일 (참고용)
#     ├── Dockerfile.backend
#     ├── Dockerfile.frontend
#     ├── docker-entrypoint.sh
#     ├── nginx.conf
#     └── .env                  # 환경변수 (시크릿 포함 — 주의)
# ============================================================================
set -euo pipefail

# ── 경로 설정 ────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_ROOT="${1:-$SCRIPT_DIR/backups}"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$BACKUP_ROOT/webmcp_backup_$STAMP"
DB_ONLY="${DB_ONLY:-false}"
[ "${1:-}" = "--db-only" ] && DB_ONLY=true

# ── 1. 백업 디렉터리 생성 ─────────────────────────────────────
mkdir -p "$BACKUP_DIR"
echo "📁 백업 디렉터리: $BACKUP_DIR"

# ── 2. ⭐ PostgreSQL 덤프 (가장 중요) ─────────────────────────
echo "🗄️  [1/2] PostgreSQL 운영 DB 덤프 중..."
if docker compose ps postgres >/dev/null 2>&1 && docker compose exec -T postgres pg_isready -U webmcp -d webmcp >/dev/null 2>&1; then
  docker compose exec -T postgres pg_dump -U webmcp -d webmcp --clean --if-exists > "$BACKUP_DIR/postgres_dump.sql"
  echo "   ✅ postgres_dump.sql ($(wc -l < "$BACKUP_DIR/postgres_dump.sql")줄)"
  # 덤프에 실제 데이터가 있는지 확인
  DATA_LINES=$(grep -cE "INSERT INTO|COPY " "$BACKUP_DIR/postgres_dump.sql" || true)
  echo "   📊 데이터 행 포함: $DATA_LINES"
else
  echo "   ⚠️  postgres 컨테이너가 실행 중이 아닙니다. 덤프를 건너뜁니다."
fi

# ── 3. 설정 파일 복사 (부차적) ─────────────────────────────────
if [ "$DB_ONLY" = "true" ]; then
  echo "ℹ️  --db-only 모드: 설정 파일 복사 생략"
else
  echo "📄 [2/2] 설정 파일 복사 중 (참고용)..."
  for f in docker-compose.yml Dockerfile.backend Dockerfile.frontend docker-entrypoint.sh nginx.conf; do
    if [ -f "$SCRIPT_DIR/$f" ]; then
      cp "$SCRIPT_DIR/$f" "$BACKUP_DIR/$f"
    fi
  done
  # .env (시크릿 포함 — 백업 시 주의)
  if [ -f "$SCRIPT_DIR/../saas/backend/.env" ]; then
    cp "$SCRIPT_DIR/../saas/backend/.env" "$BACKUP_DIR/.env"
    echo "   ⚠️  .env (시크릿) 포함됨 — 안전한 곳에 보관하세요"
  fi
fi

# ── 4. 완료 ───────────────────────────────────────────────────
echo ""
echo "✅ 백업 완료: $BACKUP_DIR"
echo ""
echo "⭐ DB 복원 방법 (가장 중요):"
echo "  docker compose exec -T postgres psql -U webmcp -d webmcp < $BACKUP_DIR/postgres_dump.sql"
echo "  또는 ./restore.sh"
