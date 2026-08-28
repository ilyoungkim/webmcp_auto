"""위젯 JS 난독화·최적화 유틸리티.

bundle.zip 에 포함되는 JS 파일(webmcp.js, widget.js, webmcp-widget.js)을
terser 로 난독화(mangle) + 최적화(compress)한다.

- widget.css 는 스타일시트라 난독화 대상이 아니다.
- webmcp-config.js 는 사용자가 수정해야 하는 설정 파일이라 난독화하지 않는다.
- terser 가 없으면 원본 JS 를 그대로 반환한다 (폴백).
"""
from __future__ import annotations

import shutil
import subprocess

from django.conf import settings


def _find_terser() -> list[str] | None:
    """terser 실행 명령(인자 포함)을 반환한다. 없으면 None.

    예: 'npx --no-install terser' → ['npx', '--no-install', 'terser']
    """
    cmd = getattr(settings, 'TERSER_CMD', 'npx --no-install terser')
    parts = cmd.split()
    if not parts:
        return None
    if parts[0] == 'npx':
        if shutil.which('npx') is None:
            return None
        return parts
    if shutil.which(parts[0]) is None:
        return None
    return parts


def minify_js(source: str) -> str:
    """JS 소스를 terser 로 난독화+최적화한다. 실패/미설치 시 원본 반환."""
    if not source or not source.strip():
        return source

    cmd_parts = _find_terser()
    if cmd_parts is None:
        return source

    cwd = getattr(settings, 'TERSER_CWD', None)
    cmd = [*cmd_parts, '--compress', '--mangle', '--toplevel']
    try:
        proc = subprocess.run(
            cmd,
            input=source,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=cwd,
        )
    except (OSError, subprocess.TimeoutExpired):
        return source
    if proc.returncode != 0:
        return source
    out = proc.stdout.strip()
    return out if out else source
