#!/usr/bin/env bash
# ============================================================================
# webmcp/dashboard/run.sh — Streamlit 대시보드 실행 스크립트
# ============================================================================
# 사용법:
#   ./run.sh            # 기본 포트(8501)로 실행
#   ./run.sh 8502       # 지정 포트로 실행
# ============================================================================
set -e

cd "$(dirname "$0")"

PORT="${1:-8501}"

# .env 파일이 없으면 .env.example 에서 복사
if [ ! -f .env ]; then
  echo "⚠️  .env 파일이 없어 .env.example 에서 복사합니다."
  echo "   실제 DB 접속 정보로 수정하세요."
  cp .env.example .env
fi

echo "🚀 WebMCP 대시보드를 포트 ${PORT} 에서 실행합니다."
echo "   http://localhost:${PORT}"

exec streamlit run app.py --server.port "${PORT}" --server.address 0.0.0.0
