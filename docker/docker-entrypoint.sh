#!/usr/bin/env bash
set -e

echo "== migrate =="
python manage.py migrate --noinput

echo "== seed_catalogs =="
python manage.py seed_catalogs || true

echo "== seed_admin =="
python manage.py seed_admin || echo "ADMIN_SEED_PASSWORD 미설정 — 관리자 시드 생략"

echo "== collectstatic =="
python manage.py collectstatic --noinput || true

echo "== gunicorn =="
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${GUNICORN_WORKERS:-2}" \
  --threads "${GUNICORN_THREADS:-2}" \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
