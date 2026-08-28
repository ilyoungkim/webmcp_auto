# ============================================================================
# webmcp/backend/run.sh — 백엔드 실행 스크립트
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")"

if ! python3 -c "import fastapi" 2>/dev/null; then
  pip3 install -r requirements.txt
fi

exec uvicorn app:app --host 0.0.0.0 --port "${PORT:-8001}"
