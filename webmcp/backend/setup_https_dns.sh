#!/usr/bin/env bash
# ============================================================================
# setup_https_dns.sh — DNS-01 방식 HTTPS 인증서 발급 (80 포트 불필요)
# ============================================================================
# DuckDNS 토큰을 이용한 DNS-01 챌린지로 인증서를 발급합니다.
# haproxy(80 포트)와 충돌하지 않습니다.
#
#   sudo bash setup_https_dns.sh
# ============================================================================
set -euo pipefail

DOMAIN="webmcp.duckdns.org"
EMAIL="tensun10@gmail.com"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ "$(id -u)" -ne 0 ]; then
  echo "❌ root 권한으로 실행하세요: sudo bash $0"
  exit 1
fi

echo "==> [1/5] certbot-dns-duckdns 플러그인 설치 (certbot과 같은 경로)"
# certbot은 /usr/lib/python3.12/site-packages 사용
pip3 install --target /usr/lib/python3.12/site-packages certbot-dns-duckdns 2>&1 | tail -3 || {
  echo "pip 설치 실패 → dnf 시도"
  dnf install -y python3-certbot-dns-duckdns
}

echo "==> [2/5] DuckDNS 인증정보 파일 배치 (권한 600)"
mkdir -p /etc/letsencrypt
cp "$SCRIPT_DIR/duckdns.ini" /etc/letsencrypt/duckdns.ini
chmod 600 /etc/letsencrypt/duckdns.ini

echo "==> [3/5] DNS-01 방식 인증서 발급"
if [ -d "/etc/letsencrypt/live/$DOMAIN" ]; then
  echo "   기존 인증서 감지 → 갱신"
  certbot renew --cert-name "$DOMAIN" --authenticator dns-duckdns \
    --dns-duckdns-credentials /etc/letsencrypt/duckdns.ini \
    --dns-duckdns-propagation-seconds 60 || true
else
  certbot certonly \
    --authenticator dns-duckdns \
    --dns-duckdns-credentials /etc/letsencrypt/duckdns.ini \
    --dns-duckdns-propagation-seconds 60 \
    -d "$DOMAIN" \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --non-interactive
fi

echo "==> [4/5] HTTPS(443) nginx 설정 배치"
cp "$SCRIPT_DIR/webmcp_https_standalone.conf" /etc/nginx/webmcp_https_standalone.conf
nginx -c /etc/nginx/webmcp_https_standalone.conf -t

echo "==> [5/5] HTTPS nginx 시작"
# 기존에 실행 중이면 reload, 아니면 start
if [ -f /run/nginx-webmcp-https.pid ] && kill -0 "$(cat /run/nginx-webmcp-https.pid)" 2>/dev/null; then
  nginx -s reload -c /etc/nginx/webmcp_https_standalone.conf
else
  nginx -c /etc/nginx/webmcp_https_standalone.conf
fi

echo ""
echo "✅ 완료! 접속: https://$DOMAIN"
echo ""
echo "📅 자동 갱신 타이머: systemctl list-timers | grep certbot"
