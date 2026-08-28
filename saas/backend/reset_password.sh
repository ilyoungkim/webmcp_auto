#!/usr/bin/env bash
# WebMCP Auto — 비밀번호 초기화 스크립트
#
# 사용법:
#   ./reset_password.sh <email> <new_password> [--no-force-change]
#
# 예시:
#   ./reset_password.sh tensun@naver.com test1234 --no-force-change
#   ./reset_password.sh admin@local test1234
#
# 기본은 다음 로그인 시 비밀번호 변경을 강제(must_change_password=True)한다.
# 바로 로그인만 필요하면 --no-force-change 를 붙인다.
set -euo pipefail
cd "$(dirname "$0")"

if [ $# -lt 2 ]; then
  echo "사용법: $0 <email> <new_password> [--no-force-change]" >&2
  exit 1
fi

source .venv/bin/activate
python manage.py reset_password "$@"