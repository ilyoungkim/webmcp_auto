"""다국어 사일로(lang silo) 모듈 — 언어별 완전 독립 실행 지원.

설계 개념
---------
WebMCP Auto를 여러 언어 버전으로 배포할 수 있어야 한다.
- 어떤 서버에는 한국어(ko)만, 어떤 곳에는 영어(en)만, 어떤 곳은 둘 다 지원하도록 설치.
- 언어마다 다른 LLM 엔진/엔드포인트, 다른 카탈로그 소스, 다른 DB 스키마(또는 별도 DB)를
  사용해 각 언어가 독립된 사일로처럼 동작한다.
- 도커는 언어별 컨테이너(compose)로 분리 실행한다.

사일로 격리 축
    1) 엔진  : WEBMCP_LANG → GEMINI_API_KEY_<LANG>, GEMINI_MODEL_<LANG>,
               OPENROUTER_MODEL_<LANG> 등 언어 접미사 env 오버라이드
    2) 소스   : 카탈로그(도메인유형/빠른메뉴)를 `lang` 태그로 저장·조회
    3) 스키마 : DB_TABLE_PREFIX_<LANG> 로 테이블 분리, or 아예 별도 DATABASE_URL
    4) 컨테이너: compose profile(webmcp-ko / webmcp-en) 별로 독립 스택 실행
"""
from __future__ import annotations

import os

from django.conf import settings

# 지원하는 언어 코드 (새 언어 추가 시 여기와 .env만 확장하면 된다)
SUPPORTED_LANGS = ('ko', 'en')

_LANG_META = {
    'ko': {'label': '한국어', 'label_en': 'Korean', 'widget_lang': 'ko', 'engine_note': '한국어 사일로'},
    'en': {'label': 'English', 'widget_lang': 'en', 'engine_note': 'English silo'},
}


def env(key: str, default: str = '') -> str:
    return os.environ.get(key, default) or ''


def configured_langs() -> list[str]:
    """이 배포(사일로 집합)에서 활성화된 언어 목록.

    .env의 WEBMCP_LANGS 로 결정한다. 예) 'ko', 'en', 'ko,en'
    기본값은 'ko'(기존 설치와 호환).
    """
    raw = env('WEBMCP_LANGS', 'ko')
    langs = [x.strip().lower() for x in raw.split(',') if x.strip() in SUPPORTED_LANGS]
    return langs or ['ko']


def current_lang() -> str:
    """이 프로세스가 담당하는 기본 언어. 미설정 시 'ko'."""
    lang = env('WEBMCP_LANG', 'ko')
    return lang if lang in SUPPORTED_LANGS else 'ko'


def lang_meta(lang: str) -> dict:
    m = dict(_LANG_META.get(lang, {}))
    m.setdefault('label', lang)
    m['code'] = lang
    m['enabled'] = supported(lang)
    return m


def silo_summary() -> dict:
    """현재 프로세스의 사일로 요약 정보 (운영 점검용)."""
    lang = current_lang()
    gk, gm, _ = gemini_config(lang)
    orc = openrouter_config(lang)
    return {
        'lang': lang,
        'label': _LANG_META.get(lang, {}).get('label', lang),
        'configured': configured_langs(),
        'catalogLang': catalog_lang_tag(lang),
        'dbTablePrefix': db_table_prefix(lang),
        'engines': {
            'gemini_model': gm,
            'openrouter_model': orc['model'],
            'openrouter_fallback': orc['fallback'],
            'gemini_key_set': bool(gk),
            'openrouter_key_present': bool(orc['api_key']),
        },
    }


def catalog_lang_tag(lang: str | None = None) -> str:
    return (lang or current_lang()).lower()


def supported(lang: str) -> bool:
    return lang in configured_langs()


def db_table_prefix(lang: str | None = None) -> str:
    """언어별 DB 테이블 접두어. 'en' → 'en_' (테이블 분리 사일로).

    .env의 DB_TABLE_PREFIX_EN 등에서 읽는다. 기본 ko는 접두어 없음.
    """
    lang = lang or current_lang()
    if lang == 'ko':
        return ''
    return env(f'WEBMCP_TABLE_PREFIX_{lang.upper()}', f'{lang}_')


# ── LLM 엔진 해석 ─────────────────────────────────────────────
# 언어별 접미사 키가 .env에 있으면 그것을 우선 사용하고, 없으면 전역 값을 쓴다.
# 이렇게 하면 "언어별로 다른 엔진/엔드포인트"를 점진적 도입할 수 있다.
def gemini_config(lang: str | None = None, project=None) -> tuple[str, str, str]:
    """(api_key, model, base) — lang 접미사 키 우선, 전역 폴백. project 테넌트 설정이 최우선."""
    lang = (lang or current_lang()).lower()
    s = '' if lang == 'ko' else f'_{lang.upper()}'

    if lang == 'ko':
        model = env('GEMINI_MODEL') or getattr(settings, 'GEMINI_MODEL', '')
        key = env('GEMINI_API_KEY') or getattr(settings, 'GEMINI_API_KEY', '')
        base = env('GEMINI_BASE') or getattr(settings, 'GEMINI_BASE', '')
        return key, model, base

    # en 등 비기본 언어: 전용 env 키 우선, 없으면 전역값에 폴백
    model = env(f'GEMINI_MODEL{s}') or getattr(settings, 'GEMINI_MODEL', '')
    key = env(f'GEMINI_API_KEY{s}') or getattr(settings, 'GEMINI_API_KEY', '')
    base = env(f'GEMINI_BASE{s}') or getattr(settings, 'GEMINI_BASE', 'https://generativelanguage.googleapis.com/v1beta')
    return key, model, base


def openrouter_config(lang: str | None = None) -> dict:
    """언어 사일로별 OpenRouter 엔진 설정."""
    lang = (lang or current_lang()).lower()
    s = '' if lang == 'ko' else f'_{lang.upper()}'
    if lang == 'ko':
        return {
            'api_key': env('OPENROUTER_API_KEY') or getattr(settings, 'OPENROUTER_API_KEY', ''),
            'model': getattr(settings, 'OPENROUTER_MODEL', ''),
            'fallback': getattr(settings, 'OPENROUTER_FALLBACK_MODEL', ''),
        }
    return {
        'api_key': env(f'OPENROUTER_API_KEY{s}') or getattr(settings, 'OPENROUTER_API_KEY', ''),
        'model': env(f'OPENROUTER_MODEL{s}') or getattr(settings, 'OPENROUTER_MODEL', ''),
        'fallback': env(f'OPENROUTER_FALLBACK_MODEL{s}') or getattr(settings, 'OPENROUTER_FALLBACK_MODEL', ''),
    }