#!/usr/bin/env bash
# ============================================================================
# setup_https.sh — webmcp.duckdns.org HTTPS(Let's Encrypt) 설치 스크립트
# ============================================================================
# Fedora 서버(192.168.31.136)에서 실행합니다. (root 권한 필요)
#
#   sudo ./setup_https.sh
#
# 동작:
#   1) certbot 설치 (dnf, 없으면 pip)
#   2) ACME 챌린지용 웹 루트(/var/www/certbot) 생성
#   3) 1단계: HTTP(80) 블록만 배치 → nginx 재시작 (챌린지 응답 준비)
#   4) certbot 으로 인증서 발급 (HTTP-01)
#   5) 2단계: HTTPS(443) 블록 배치 → nginx 재시작
#   6) HTTP → HTTPS 리다이렉트 블록으로 교체
# ============================================================================
set -euo pipefail

DOMAIN="webmcp.duckdns.org"
EMAIL="admin@webmcp.duckdns.org"   # ← 필요 시 이메일 변경 (만료 알림용)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ "$(id -u)" -ne 0 ]; then
  echo "❌ root 권한으로 실행하세요: sudo $0"
  exit 1
fi

echo "==> [1/6] certbot 설치"
if ! command -v certbot >/dev/null 2>&1; then
  dnf install -y certbot || {
    echo "dnf 실패 → pip 로 시도"
    pip3 install certbot
  }
fi
echo "   certbot: $(command -v certbot)"

echo "==> [2/6] ACME 챌린지 웹 루트 생성"
mkdir -p /var/www/certbot

echo "==> [3/6] 1단계: HTTP(80) 블록 배치 + nginx 재시작"
cp "$SCRIPT_DIR/webmcp_http.conf" /etc/nginx/conf.d/webmcp_http.conf
nginx -t
systemctl reload nginx || nginx -s reload

echo "==> [4/6] 인증서 발급 (HTTP-01)"
if [ -d "/etc/letsencrypt/live/$DOMAIN" ]; then
  echo "   기존 인증서 감지 → 갱신 시도"
  certbot renew --cert-name "$DOMAIN" || true
else
  certbot certonly \
    --webroot -w /var/www/certbot \
    -d "$DOMAIN" \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --non-interactive
fi

echo "==> [5/6] 2단계: HTTPS(443) 블록 배치 + nginx 재시작"
cp "$SCRIPT_DIR/webmcp_https.conf" /etc/nginx/conf.d/webmcp_https.conf
nginx -t
systemctl reload nginx || nginx -s reload

echo "==> [6/6] HTTP → HTTPS 리다이렉트로 교체"
cp "$SCRIPT_DIR/webmcp_redirect.conf" /etc/nginx/conf.d/webmcp_http.conf
nginx -t
systemctl reload nginx || nginx -s reload

echo ""
echo "✅ 완료! 접속: https://$DOMAIN"
echo ""
echo "📅 자동 갱신 확인: systemctl list-timers | grep certbot"
