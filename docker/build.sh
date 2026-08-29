#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# WebMCP Auto — Docker 이미지 빌드 스크립트
# ─────────────────────────────────────────────────────────────
# 용도: Django 백엔드 + Nuxt 프론트엔드 이미지를 컴파일(빌드)한다.
#       빌드 후 자동으로 `docker compose up` 까지 할지 --run 플래그로 결정.
#
# 사용법 (docker/ 폴더에서 실행):
#   ./build.sh                  # 기본(ko) 사일로만 빌드
#   ./build.sh --silo           # ko + en 사일로 모두 빌드
#   ./build.sh --en             # en 사일로만 빌드
#   ./build.sh --no-cache       # 캐시 없이 완전 재빌드
#   ./build.sh --run            # 빌드 후 컨테이너 기동까지 (기본 ko)
#   ./build.sh --run --silo     # 빌드 후 ko(8080) + en(8081) 모두 기동
#   ./build.sh --help
# ─────────────────────────────────────────────────────────────
set -euo pipefail

# ── 색상 출력 ────────────────────────────────────────────────
if [ -t 1 ]; then
  C_G="\033[32m"; C_Y="\033[33m"; C_R="\033[31m"; C_B="\033[36m"; C_N="\033[0m"
else
  C_G=""; C_Y=""; C_R=""; C_B=""; C_N=""
fi
info() { printf "${C_B}[INFO]${C_N} %s\n" "$1"; }
ok()   { printf "${C_G}[ OK ]${C_N} %s\n" "$1"; }
warn() { printf "${C_Y}[WARN]${C_N} %s\n" "$1"; }
err()  { printf "${C_R}[FAIL]${C_N} %s\n" "$1" >&2; }

# ── 기본값 ───────────────────────────────────────────────────
BUILD_TARGET="ko"      # ko | en | all
RUN_AFTER_BUILD=false
NO_CACHE_FLAG=""

# ── 인자 파싱 ────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --silo)      BUILD_TARGET="all" ;;
    --en)        BUILD_TARGET="en" ;;
    --ko)        BUILD_TARGET="ko" ;;
    --run)       RUN_AFTER_BUILD=true ;;
    --no-cache)  NO_CACHE_FLAG="--no-cache" ;;
    -h|--help)
      sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      err "알 수 없는 인자: $arg  (--help 참고)"
      exit 1
      ;;
  esac
done

# ── 사전 조건 확인 ───────────────────────────────────────────
cd "$(dirname "$0")"   # docker/ 폴더 기준 실행 보장

if ! command -v docker > /dev/null 2>&1; then
  err "docker가 설치되어 있지 않거나 PATH에 없습니다."
  exit 1
fi

if ! docker info > /dev/null 2>&1; then
  err "Docker daemon이 실행 중이지 않습니다. Docker Desktop을 시작해 주세요."
  exit 1
fi

# .env 존재 확인 (LLM 키 등) — 없으면 경고 후 계속
if [ ! -f ../saas/backend/.env ]; then
  warn "saas/backend/.env 파일이 없습니다. LLM 키가 없으면 Q&A 생성과 채팅이 동작하지 않습니다."
fi

# ── 빌드 함수 ────────────────────────────────────────────────
build_compose() {
  local compose_file="$1"
  local label="$2"
  info "── ${label} 이미지 빌드 시작 (${compose_file}) ──"
  # shellcheck disable=SC2086
  docker compose -f "${compose_file}" build ${NO_CACHE_FLAG} \
    || { err "${label} 빌드 실패"; exit 1; }
  ok "${label} 이미지 빌드 완료"
}

run_compose() {
  local compose_file="$1"
  local label="$2"
  info "── ${label} 컨테이너 기동 ──"
  docker compose -f "${compose_file}" up -d \
    || { err "${label} 기동 실패"; exit 1; }
}

# ── 빌드 실행 ────────────────────────────────────────────────
START_TS=$(date +%s)
info "빌드 대상: ${BUILD_TARGET}  |  no-cache: ${NO_CACHE_FLAG:-no}  |  run: ${RUN_AFTER_BUILD}"

case "$BUILD_TARGET" in
  ko)
    build_compose docker-compose.yml "기본(ko) 사일로"
    ;;
  en)
    build_compose docker-compose.silo.yml "영어(en) 사일로"
    ;;
  all)
    build_compose docker-compose.yml "기본(ko) 사일로"
    build_compose docker-compose.silo.yml "영어(en) 사일로"
    ;;
esac

ELAPSED=$(( $(date +%s) - START_TS ))

# ── 기동 (옵션) ──────────────────────────────────────────────
if [ "$RUN_AFTER_BUILD" = true ]; then
  case "$BUILD_TARGET" in
    ko)
      run_compose docker-compose.yml "기본(ko) 사일로"
      ok "ko 사일로 기동 완료 → http://localhost:8080"
      ;;
    en)
      run_compose docker-compose.silo.yml "영어(en) 사일로"
      ok "en 사일로 기동 완료 → http://localhost:8081 (en 위젯·콘솔)"
      ;;
    all)
      run_compose docker-compose.yml "기본(ko) 사일로"
      run_compose docker-compose.silo.yml "영어(en) 사일로"
      ok "ko 사일로 기동 완료 → http://localhost:8080"
      ok "en 사일로 기동 완료 → http://localhost:8081"
      ;;
  esac

  # health 체크 (backend 준비 대기)
  info "backend 준비 대기 중..."
  for i in $(seq 1 15); do
    sleep 2
    KO_HEALTH=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/health/ 2>/dev/null || echo "000")
    if [ "${KO_HEALTH}" = "200" ]; then
      ok "ko backend ready (시도 ${i}/15)"
      break
    fi
  done
  if [ "$BUILD_TARGET" != "ko" ]; then
    for i in $(seq 1 15); do
      sleep 2
      EN_HEALTH=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8081/health/ 2>/dev/null || echo "000")
      if [ "${EN_HEALTH}" = "200" ]; then
        ok "en backend ready (시도 ${i}/15)"
        break
      fi
    done
  fi
fi

ok "전체 완료 — 소요 ${ELAPSED}초"
echo ""
echo "  접속 주소:"
echo "    ko 사일로 : http://localhost:8080   (한국어 콘솔·위젯)"
echo "    en 사일로 : http://localhost:8081   (English console·widget)"
echo ""
echo "  로그 확인  : docker compose -f docker-compose.silo.yml logs -f backend-en"
echo "  정지       : docker compose down && docker compose -f docker-compose.silo.yml down"