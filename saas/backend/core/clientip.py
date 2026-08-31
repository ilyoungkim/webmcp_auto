"""요청 클라이언트 IP 추출·정제.

프록시(IIS ARR, nginx 등)마다 X-Forwarded-For / REMOTE_ADDR 형식이 다르다:
- nginx: '1.2.3.4, 10.0.0.1' (포트 없음)
- IIS ARR/X-Forwarded-For: '1.2.3.4:56789', '[::1]:58464' (포트 포함)

PostgreSQL inet 컬럼(Django GenericIPAddressField)은 순수 IP만 허용하므로
반드시 정제 후 사용한다.
"""
from __future__ import annotations

import ipaddress


def normalize_ip(raw: str | None) -> str | None:
    """'IP:포트'·'[IPv6]:포트' 형태를 순수 IP로 정제. 유효하지 않으면 None.

    >>> normalize_ip('1.2.3.4')
    '1.2.3.4'
    >>> normalize_ip('1.2.3.4:56789')
    '1.2.3.4'
    >>> normalize_ip('[::1]:58464')
    '::1'
    >>> normalize_ip('::1')
    '::1'
    >>> normalize_ip('garbage') is None
    True
    """
    raw = (raw or '').strip()
    if not raw:
        return None
    try:
        ipaddress.ip_address(raw)
        return raw  # 이미 순수 IP
    except ValueError:
        pass
    # '[::1]:58464' — 브래킷 IPv6 + 포트
    if raw.startswith('['):
        end = raw.find(']')
        if end == -1:
            return None
        raw = raw[1:end]
    # '127.0.0.1:64171' — IPv4 + 포트 (IPv6는 ':'가 2개 이상)
    elif raw.count(':') == 1 and '.' in raw:
        raw = raw.rsplit(':', 1)[0]
    try:
        ipaddress.ip_address(raw)
        return raw
    except ValueError:
        return None


def client_ip(request) -> str | None:
    """Django request에서 클라이언트 IP 추출 후 정제. X-Forwarded-For 우선."""
    fwd = request.META.get('HTTP_X_FORWARDED_FOR')
    raw = fwd.split(',')[0].strip() if fwd else (request.META.get('REMOTE_ADDR') or '')
    return normalize_ip(raw)