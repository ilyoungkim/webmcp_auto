#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# WebMCP Auto — Docker 이미지 빌드/기동 스크립트 (언어 사일로 관리)
# ─────────────────────────────────────────────────────────────
# 기본값: ko + en 모두 빌드(및 --run 시 모두 기동).
# --ko / --en 으로 특정 언어 사일로만 대상 지정.
# 새 언어(ja, zh, fr, es, pt...)는 LANG_REGISTRY에 한 줄만 추가하면 된다.
#
# 사용법 (docker/ 폴더에서 실행):
#   ./build.sh                    # ko + en 모두 빌드 (기본)
#   ./build.sh --ko               # ko 사일로만 빌드
#   ./build.sh --en               # en 사일로만 빌드
#   ./build.sh --run              # 빌드 + ko/en 모두 기동 + health 체크
#   ./build.sh --run ko           # 빌드 + ko(8080)만 기동
#   ./build.sh --run en           # 빌드 + en(8081)만 기동
#   ./build.sh --no-cache --run   # 캐시 무시 완전 재빌드 후 기동
#   ./build.sh --dry-run          # 실행할 명령만 출력 (실제 빌드 안 함)
#   ./build.sh --list             # 등록된 언어 사일로 목록
#   ./build.sh --help
# ─────────────────────────────────────────────────────────────
set -euo pipefail

# ── 색상 출력 ────────────────────────────────────────────────
if [ -t 1 ]; then
  C_G="\033[32m"; C_Y="\033[33m"; C_R="\033[31m"; C_B="\033[36m"; C_M="\033[35m"; C_N="\033[0m"
else
  C_G=""; C_Y=""; C_R=""; C_B=""; C_M=""; C_N=""
fi
info() { printf "${C_B}[INFO]${C_N} %s\n" "$1"; }
ok()   { printf "${C_G}[ OK ]${C_N} %s\n" "$1"; }
warn() { printf "${C_Y}[WARN]${C_N} %s\n" "$1"; }
err()  { printf "${C_R}[FAIL]${C_N} %s\n" "$1" >&2; }
plan() { printf "${C_M}[PLAN]${C_N} %s\n" "$1"; }

# ── 언어 사일로 레지스트리 ───────────────────────────────────
# 형식: 언어코드:compose파일:표시라벨:접속주소
# 새 언어 추가 방법:
#   1) docker-compose 파일에 <lang> 사일로 서비스 추가 (backend-<lang> 등)
#   2) 아래에 LANGS_XX="xx:docker-compose.xx.yml:...:http://localhost:POTR" 한 줄 추가 후 ALL_LANGS에 등록
#   3) saas/backend/core/langsilo.py 의 SUPPORTED_LANGS 도 함께 확장
#   4) ./build.sh --run xx  로 빌드·기동
LANGS_KO="ko:docker-compose.yml:한국어(ko) 사일로:http://localhost:8080"
LANGS_EN="en:docker-compose.silo.yml:영어(en) 사일로:http://localhost:8081"
# LANGS_JA="ja:docker-compose.ja.yml:일본어(ja) 사일로:http://localhost:8082"
# LANGS_ZH="zh:docker-compose.zh.yml:중국어(zh) 사일로:http://localhost:8083"
# LANGS_FR="fr:docker-compose.fr.yml:프랑스어(fr) 사일로:http://localhost:8084"
# LANGS_ES="es:docker-compose.es.yml:스페인어(es) 사일로:http://localhost:8085"
# LANGS_PT="pt:docker-compose.pt.yml:포르투갈어(pt) 사일로:http://localhost:8086"

ALL_LANGS=("${LANGS_KO}" "${LANGS_EN}")
# 새 언어 활성화 시 위 주석을 풀고 여기에 추가: ALL_LANGS+=( "${LANGS_JA}" "${LANGS_ZH}" ... )

lang_code()  { echo "$1" | cut -d: -f1; }
lang_file()  { echo "$1" | cut -d: -f2; }
lang_label() { echo "$1" | cut -d: -f3; }
lang_url()   { echo "$1" | cut -d: -f4-; }

# ── 기본값 ───────────────────────────────────────────────────
RUN_AFTER_BUILD=false
NO_CACHE_FLAG=""
DRY_RUN=false
TARGET_LANGS=()     # 비었으면 전체(ko+en)
EXPLICIT_TARGET=false

# ── 도움말 ───────────────────────────────────────────────────
show_help() {
cat <<'EOF'
WebMCP Auto — Docker 이미지 빌드/기동 스크립트 (언어 사일로 관리)

사용법 (docker/ 폴더에서 실행):

  빌드 (기본: ko + en 모두)
    ./build.sh                  # ko + en 모두 빌드
    ./build.sh --ko             # ko 사일로만 빌드
    ./build.sh --en             # en 사일로만 빌드
    ./build.sh --no-cache       # 캐시 무시 완전 재빌드

  빌드 + 기동
    ./build.sh --run            # ko + en 모두 기동 + health 체크
    ./build.sh --run ko         # ko(8080)만 기동
    ./build.sh --run en         # en(8081)만 기동

  기타
    ./build.sh --dry-run        # 실행할 명령만 출력 (실제 빌드 안 함)
    ./build.sh --list           # 등록된 언어 사일로 목록
    ./build.sh --help           # 이 도움말

  새 언어 추가 (예: 일본어)
    1) docker-compose.ja.yml 로 사일로 스택 정의 (포트 8082 등)
    2) 본 스크립트 상단 LANGS_JA 주석 해제 + ALL_LANGS에 추가
    3) saas/backend/core/langsilo.py 의 SUPPORTED_LANGS 확장
    4) ./build.sh --run ja
EOF
}

# ── 인자 파싱 ────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --ko)       TARGET_LANGS+=("ko"); EXPLICIT_TARGET=true ;;
    --en)       TARGET_LANGS+=("en"); EXPLICIT_TARGET=true ;;
    --run)      RUN_AFTER_BUILD=true ;;
    --no-cache) NO_CACHE_FLAG="--no-cache" ;;
    --dry-run)  DRY_RUN=true ;;
    --list)
      info "등록된 언어 사일로:"
      for entry in "${ALL_LANGS[@]}"; do
        printf "  %-3s %-28s %s\n" "$(lang_code "$entry")" "$(lang_file "$entry")" "$(lang_url "$entry")"
      done
      exit 0
      ;;
    -h|--help)  show_help; exit 0 ;;
    ko|en)
      TARGET_LANGS+=("$arg"); EXPLICIT_TARGET=true ;;
    *)
      err "알 수 없는 인자: $arg  (--help 참고)"
      exit 1
      ;;
  esac
done

# ── 대상 언어 확정 ───────────────────────────────────────────
if [ "$EXPLICIT_TARGET" = false ]; then
  # 기본: 레지스트리의 모든 활성 언어
  TARGET_LANGS=()
  for entry in "${ALL_LANGS[@]}"; do
    TARGET_LANGS+=("$(lang_code "$entry")")
  done
fi

# ── 사전 조건 확인 ───────────────────────────────────────────
cd "$(dirname "$0")"   # docker/ 폴더 기준 실행 보장

if [ "$DRY_RUN" = false ]; then
  if ! command -v docker > /dev/null 2>&1; then
    err "docker가 설치되어 있지 않거나 PATH에 없습니다."
    exit 1
  fi
  if ! docker info > /dev/null 2>&1; then
    err "Docker daemon이 실행 중이지 않습니다. Docker Desktop을 시작해 주세요."
    exit 1
  fi
  if [ ! -f ../saas/backend/.env ]; then
    warn "saas/backend/.env 파일이 없습니다. LLM 키가 없으면 Q&A 생성과 채팅이 동작하지 않습니다."
  fi
fi

# 언어 코드→레지스트리 엔트리 찾기
find_entry() {
  local code="$1"
  for entry in "${ALL_LANGS[@]}"; do
    if [ "$(lang_code "$entry")" = "$code" ]; then
      echo "$entry"
      return 0
    fi
  done
  return 1
}

# ── 실행 계획 요약 ───────────────────────────────────────────
START_TS=$(date +%s)
TARGET_SUMMARY=$(printf "%s " "${TARGET_LANGS[@]}")
info "대상 언어  : ${TARGET_SUMMARY}"
info "옵션       : no-cache=${NO_CACHE_FLAG:+yes} run=${RUN_AFTER_BUILD} dry-run=${DRY_RUN}"

if [ "$DRY_RUN" = true ]; then
  warn "DRY-RUN 모드 — 실제로는 실행하지 않고 명령만 출력합니다."
fi

# 대상 유효성 미리 검증 + compose 파일 존재 확인
for lang in "${TARGET_LANGS[@]}"; do
  if ! entry=$(find_entry "$lang"); then
    err "미등록 언어: ${lang} — ./build.sh --list 로 확인"
    exit 1
  fi
  file=$(lang_file "$entry")
  label=$(lang_label "$entry")
  if [ ! -f "$file" ]; then
    err "compose 파일 없음: ${file} (${label})"
    exit 1
  fi
done

# ── 빌드 ─────────────────────────────────────────────────────
for lang in "${TARGET_LANGS[@]}"; do
  entry=$(find_entry "$lang")
  file=$(lang_file "$entry")
  label=$(lang_label "$entry")
  info "── ${label} 이미지 빌드 (${file}) ──"
  if [ "$DRY_RUN" = true ]; then
    plan "docker compose -f ${file} build ${NO_CACHE_FLAG}"
  else
    # shellcheck disable=SC2086
    docker compose -f "${file}" build ${NO_CACHE_FLAG} \
      || { err "${label} 빌드 실패"; exit 1; }
    ok "${label} 이미지 빌드 완료"
  fi
done

# ── 기동 (옵션) ──────────────────────────────────────────────
if [ "$RUN_AFTER_BUILD" = true ]; then
  for lang in "${TARGET_LANGS[@]}"; do
    entry=$(find_entry "$lang")
    file=$(lang_file "$entry")
    label=$(lang_label "$entry")
    url=$(lang_url "$entry")
    info "── ${label} 컨테이너 기동 ──"
    if [ "$DRY_RUN" = true ]; then
      plan "docker compose -f ${file} up -d"
    else
      docker compose -f "${file}" up -d \
        || { err "${label} 기동 실패"; exit 1; }
      ok "${label} 기동 완료 → ${url}"
    fi
  done

  # health 체크 (기동한 언어만)
  if [ "$DRY_RUN" = false ]; then
    info "backend 준비 대기 중..."
    for lang in "${TARGET_LANGS[@]}"; do
      entry=$(find_entry "$lang")
      url=$(lang_url "$entry")
      ready=false
      for i in $(seq 1 15); do
        sleep 2
        CODE=$(curl -s -o /dev/null -w '%{http_code}' "${url}/health/" 2>/dev/null || echo "000")
        if [ "${CODE}" = "200" ]; then
          ok "$(lang_code "$entry") backend ready (시도 ${i}/15)"
          ready=true
          break
        fi
      done
      if [ "$ready" = false ]; then
        warn "$(lang_code "$entry") health 미응답 — 로그 확인: docker compose -f $(lang_file "$entry") logs backend"
      fi
    done
  fi
fi

ELAPSED=$(( $(date +%s) - START_TS ))
ok "전체 완료 — 소요 ${ELAPSED}초"
echo ""
echo "  접속 주소:"
for lang in "${TARGET_LANGS[@]}"; do
  entry=$(find_entry "$lang")
  printf "    %-3s %s   %s\n" "$(lang_code "$entry")" "$(lang_url "$entry")" "$(lang_label "$entry")"
done
echo ""
echo "  로그 확인  : docker compose -f docker-compose.silo.yml logs -f"
echo "  정지       : docker compose down && docker compose -f docker-compose.silo.yml down"