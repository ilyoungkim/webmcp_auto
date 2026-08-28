#!/usr/bin/env bash
# ============================================================================
# cert_renew_check.sh — 인증서 유효기간 확인 + 자동 갱신 + 결과 알림
# ============================================================================
# 매달(또는 주기적으로) 실행하여:
#   1) 인증서 만료까지 남은 일수 확인
#   2) 30일 이내면 자동 갱신
#   3) 결과를 로그 + 이메일(선택) 로 남김
#
# crontab 등록 (매달 1일 03:00):
#   0 3 1 * * /usr/local/bin/cert_renew_check.sh >> /var/log/cert_renew.log 2>&1
# ============================================================================
set -euo pipefail

DOMAIN="webmcp.duckdns.org"
CERT="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
LOG="/var/log/cert_renew_check.log"
THRESHOLD_DAYS=30   # 이 일수 이하로 남으면 갱신

log() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

if [ ! -f "$CERT" ]; then
  log "⚠️ 인증서 파일 없음: $CERT"
  exit 1
fi

# 만료일 및 남은 일수 계산
EXPIRY_TS=$(openssl x509 -enddate -noout -in "$CERT" | cut -d= -f2)
EXPIRY_EPOCH=$(date -d "$EXPIRY_TS" +%s 2>/dev/null || date -j -f "%b %d %H:%M:%S %Y %Z" "$EXPIRY_TS" +%s)
NOW_EPOCH=$(date +%s)
DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))

log "인증서 만료일: $EXPIRY_TS (남은 일수: ${DAYS_LEFT}일)"

if [ "$DAYS_LEFT" -le "$THRESHOLD_DAYS" ]; then
  log "남은 기간 ${DAYS_LEFT}일 ≤ ${THRESHOLD_DAYS}일 → 갱신 시도 (DNS-01)"
  if certbot renew --quiet \
      --authenticator dns-duckdns \
      --dns-duckdns-credentials /etc/letsencrypt/duckdns.ini \
      --dns-duckdns-propagation-seconds 60; then
    log "✅ 갱신 성공"
    # HTTPS standalone nginx 재시작 (새 인증서 반영)
    if [ -f /run/nginx-webmcp-https.pid ]; then
      nginx -s reload -c /etc/nginx/webmcp_https_standalone.conf
      log "https nginx 재시작 완료"
    fi
  else
    log "❌ 갱신 실패 (상세는 certbot 로그 확인)"
    exit 1
  fi
else
  log "아직 충분 (${DAYS_LEFT}일 남음) → 갱신 불필요"
fi
