#!/usr/bin/env bash
# ── 워커 전용 entrypoint (Render dockerCommand용) ──────────────
# Render는 dockerCommand를 셸로 감싸 전달하므로 "cmd1 && cmd2" 체인이
# 파일명으로 오판되어 크래시 루프에 빠진다(실측). 체인은 스크립트로 해결.
set -e

echo "== worker: migrate =="
python manage.py migrate --noinput

echo "== worker: run_pipeline_worker =="
exec python manage.py run_pipeline_worker --interval 2.0