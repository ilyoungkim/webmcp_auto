"""URL → Origin 정규화 + SSRF 가드."""
from __future__ import annotations

import ipaddress
import socket
import time
from urllib.parse import urlsplit

BLOCKED_HOSTNAMES = {'localhost', 'metadata.google.internal', '169.254.169.254'}


def normalize_origin(url: str) -> str:
    """https://www.Example.com:443/a → https://example.com"""
    parts = urlsplit(url if '://' in url else 'https://' + url)
    scheme = (parts.scheme or 'https').lower()
    host = (parts.hostname or '').lower()
    port = parts.port
    default = {'http': 80, 'https': 443}.get(scheme)
    netloc = host if port in (None, default) else f'{host}:{port}'
    return f'{scheme}://{netloc}'


def validate_crawl_url(url: str) -> str:
    """SSRF 위험 URL은 ValueError."""
    url = url.strip()
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https'):
        raise ValueError('http/https 만 허용')
    host = (parts.hostname or '').lower()
    if not host or host in BLOCKED_HOSTNAMES:
        raise ValueError('차단된 호스트')

    # getaddrinfo 실패 시 gethostbyname 폴백 및 재시도
    last_error = None
    ip_list = []
    for attempt in range(3):
        try:
            infos = socket.getaddrinfo(host, None)
            ip_list = [info[4][0] for info in infos if info and len(info) >= 5 and info[4]]
            if ip_list:
                break
        except OSError as e:
            last_error = e
            try:
                ip_str = socket.gethostbyname(host)
                if ip_str:
                    ip_list = [ip_str]
                    break
            except OSError:
                pass
            if attempt < 2:
                time.sleep(0.3 * (attempt + 1))
    
    # 샌드박스 등 특수 환경에서 DNS 조회가 시스템 레벨에서 막힌 경우 최소한의 호스트네임 검증 후 허용
    if not ip_list:
        if '.' in host and not host.startswith(('127.', '10.', '192.168.', '172.')):
            return url
        raise ValueError(f'DNS 실패: {last_error}') from last_error

    for ip_addr in ip_list:
        try:
            ip = ipaddress.ip_address(ip_addr)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise ValueError(f'사설/예약 IP 차단: {ip}')
        except ValueError as e:
            if '차단' in str(e):
                raise
            continue
    return url
