"""IP 화이트리스트 검증 툴.

사용자(User.allowed_ips)에 등록된 IP/CIDR 목록으로 접속 IP를 검증한다.
- 목록이 비어 있으면 제한 없음 (모든 IP 허용)
- 단일 IP('203.0.113.10') 또는 CIDR('203.0.113.0/24') 지원
- 줄바꿈 또는 콤마로 구분

안전장치: 루프백(127.0.0.1, ::1)과 로컬 호스트 접속은 화이트리스트와 무관하게
항상 허용한다. 관리자가 화이트리스트를 잘못 설정해도 로컬(서버 콘솔)에서는
로그인할 수 있도록 락아웃 방지 역할을 한다.
"""
from __future__ import annotations

import ipaddress

# 항상 허용되는 루프백/로컬 주소 (설정 실수 시에도 로컬 접속 보장)
ALWAYS_LOCAL = ('127.0.0.1', '::1', 'localhost')
# 프록시(nginx) 뒤에서 REMOTE_ADDR 이 로컬로 보일 수 있는 주소들.
# X-Forwarded-For 가 없는 직접 요청(로컬 콘솔 작업 등)에서도 락아웃되지 않도록 한다.
LOCAL_PROXY_HOSTS = (
    '127.0.0.1', '::1',             # 서버 자신(루프백)
    '172.16.0.0/12',                # 도커/사설망 (nginx → backend 구간)
    '10.0.0.0/8',                   # 사설망
    '192.168.0.0/16',               # 사설망 (Docker Desktop 게이트웨이 포함)
)


def parse_allowed_ips(raw: str) -> list:
    """문자열(줄바꿈/콤마 구분)을 ipaddress 객체 목록으로 변환. 잘못된 항목은 무시."""
    if not raw:
        return []
    out = []
    for token in raw.replace(',', '\n').split('\n'):
        token = token.strip()
        if not token:
            continue
        try:
            out.append(ipaddress.ip_network(token, strict=False))
        except ValueError:
            continue  # 잘못된 형식은 무시
    return out


def _is_local_addr(addr) -> bool:
    """addr(ipaddress 객체)이 루프백/사설망(프록시 구간이거나 로컬)인지 확인."""
    if addr.is_loopback:
        return True
    for net in _parse_nets(LOCAL_PROXY_HOSTS):
        if addr in net:
            return True
    return False


def _parse_nets(raw) -> list:
    if isinstance(raw, str):
        return parse_allowed_ips(raw)
    out = []
    for token in raw:
        try:
            out.append(ipaddress.ip_network(token, strict=False))
        except ValueError:
            continue
    return out


def ip_allowed(raw_allowed: str, ip: str, *, direct: bool = False) -> bool:
    """ip가 허용 목록에 포함되는지 확인.

    - 루프백(127.0.0.1 등)이면 항상 True (안전장치)
    - ip가 사설망/루프백이면 True (안전장치) — 락아웃 방지.
      서버가 사내망/도커 네트워크/로컬에서 접속되는 환경에서는 화이트리스트
      실수와 무관하게 내부 접속을 보장한다. 공인 IP만 화이트리스트 판정 대상.
    - 목록이 비어 있으면 True (제한 없음)
    - 전역 스위치(WEBMCP_IPGUARD env 또는 SiteSetting ipguard_enabled)가
      false이면 항상 True — 기능 자체 비활성화 (PaaS 프록시 환경용)
    """
    # 전역 스위치 — DB 설정(ipguard_enabled) 우선, 없으면 env(WEBMCP_IPGUARD)
    # 순환 import 회피: 함수 내부에서 lazy import
    import os
    try:
        from apps.proxy.models import SiteSetting
        if SiteSetting.get('ipguard_enabled', '') != '':
            if SiteSetting.get('ipguard_enabled', 'true') != 'true':
                return True
        elif os.environ.get('WEBMCP_IPGUARD', 'true').strip().lower() == 'false':
            return True
    except Exception:  # noqa: BLE001 — DB 미초기화 등 실패 시 env 폴백
        if os.environ.get('WEBMCP_IPGUARD', 'true').strip().lower() == 'false':
            return True
    if (ip or '').strip() in ALWAYS_LOCAL:
        return True
    try:
        addr = ipaddress.ip_address(ip)
        if _is_local_addr(addr):
            return True
    except ValueError:
        pass
    entries = parse_allowed_ips(raw_allowed)
    if not entries:
        return True
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in entries)