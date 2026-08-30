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


# ── 사일로별 사용자 노출 메시지 ────────────────────────────────
# API 오류/안내 문구를 언어 사일로에 맞춰 반환한다.
# 사용법:
#   from core.langsilo import msg
#   raise ValidationError(msg('project.notFound'))
#   return Response({'detail': msg('auth.invalidCredentials')}, status=401)
#
# 새 문구 추가 시 ko/en 쌍을 함께 정의할 것 (한쪽만 있으면 ko 로 폴백).
MESSAGES = {
    # ── 공통 ──
    'common.badRequest': {'ko': '잘못된 요청', 'en': 'Bad request'},
    'common.forbidden': {'ko': '권한 없음', 'en': 'Permission denied'},
    'common.notFound': {'ko': '대상을 찾을 수 없습니다.', 'en': 'Not found.'},
    # ── 인증/계정 ──
    'auth.invalidCredentials': {'ko': '자격 증명이 올바르지 않습니다.', 'en': 'Invalid credentials.'},
    'auth.ipNotAllowed': {'ko': '허용되지 않은 IP에서의 접속입니다.', 'en': 'Access from this IP address is not allowed.'},
    'auth.tooManyAttempts': {'ko': '로그인 시도 횟수를 초과했습니다. {seconds}초 후 다시 시도하세요.', 'en': 'Too many login attempts. Please try again in {seconds} seconds.'},
    'auth.postOnly': {'ko': 'POST 만 허용됩니다.', 'en': 'Only POST is allowed.'},
    'auth.passwordMismatch': {'ko': '현재 비밀번호가 다릅니다.', 'en': 'The current password is incorrect.'},
    # ── 프로젝트 ──
    'project.notFound': {'ko': '프로젝트를 찾을 수 없습니다.', 'en': 'Project not found.'},
    'project.notFoundShort': {'ko': '프로젝트 없음', 'en': 'Project not found'},
    'project.limitReached': {'ko': '프로젝트는 최대 {max}개까지 생성할 수 있습니다.', 'en': 'You can create up to {max} projects.'},
    'project.fieldsRequired': {'ko': 'name/url/domainTypeCode 필요', 'en': 'name/url/domainTypeCode are required'},
    'project.unknownDomainType': {'ko': '알 수 없는 도메인 유형', 'en': 'Unknown domain type'},
    'project.unknownTheme': {'ko': '알 수 없는 테마', 'en': 'Unknown theme'},
    'project.urlRequired': {'ko': 'url 필요', 'en': 'url is required'},
    'project.menuEditOnce': {'ko': '빠른메뉴 질문 편집은 1회만 가능합니다.', 'en': 'Quick menu questions can be edited only once.'},
    'project.noSources': {'ko': '수집된 소스가 없습니다. 먼저 크롤링/재생성을 실행하세요.', 'en': 'No collected sources. Run crawling/regeneration first.'},
    'project.noMenus': {'ko': '빠른메뉴가 설정되지 않았습니다.', 'en': 'No quick menus configured.'},
    'project.originTaken': {'ko': '이미 다른 프로젝트에 등록된 Origin', 'en': 'Origin already registered to another project'},
    'project.originNotFound': {'ko': 'Origin 없음', 'en': 'Origin not found'},
    'project.originMinimum': {'ko': '최소 1개 Origin 은 유지해야 합니다.', 'en': 'At least one Origin must remain.'},
    'project.questionRequired': {'ko': '질문 내용을 입력해주세요.', 'en': 'Please enter a question.'},
    'project.questionTooLong': {'ko': '질문은 2000자 이내로 입력해주세요.', 'en': 'Questions must be 2000 characters or fewer.'},
    # ── 위젯 ──
    'widget.notFound': {'ko': '위젯 없음', 'en': 'Widget not found'},
    'widget.notGenerated': {'ko': '아직 생성된 위젯이 없습니다.', 'en': 'No widget has been generated yet.'},
    # ── 데이터 플레인(공개 API) ──
    'proxy.questionRequired': {'ko': 'question/publicId 필요', 'en': 'question/publicId are required'},
    'proxy.widgetNotRegistered': {'ko': '등록되지 않은 위젯', 'en': 'Widget is not registered'},
    'proxy.widgetDisabled': {'ko': '사용이 중지된 위젯입니다.', 'en': 'This widget is disabled.'},
    'proxy.domainNotAllowed': {'ko': '허용되지 않은 도메인', 'en': 'Domain not allowed'},
    'proxy.rateLimited': {'ko': '호출 한도 초과', 'en': 'Rate limit exceeded'},
    'proxy.aiFailed': {'ko': 'AI 호출 실패', 'en': 'AI request failed'},
    'proxy.errorMessageRequired': {'ko': 'errorMessage 필요', 'en': 'errorMessage is required'},
    # ── 관리자 ──
    'admin.userNotFound': {'ko': '사용자 없음', 'en': 'User not found'},
    'admin.priceMustBeNumber': {'ko': '결제 금액은 숫자여야 합니다.', 'en': 'The billing amount must be a number.'},
    'admin.reportNotFound': {'ko': '신고 없음', 'en': 'Report not found'},
    'admin.qnaNotFound': {'ko': 'Q&A 없음', 'en': 'Q&A not found'},
    'admin.answerRequired': {'ko': '답변 내용을 입력해주세요.', 'en': 'Please enter an answer.'},
}


def msg(key: str, lang: str | None = None, **params) -> str:
    """사일로 언어에 맞는 사용자 노출 메시지 반환.

    key: MESSAGES 의 키. 정의가 없으면 key 를 그대로 반환(개발 중 누락 확인용).
    params: {placeholder} 치환용 값.
    """
    lang = (lang or current_lang()).lower()
    entry = MESSAGES.get(key)
    if not entry:
        return key
    text = entry.get(lang) or entry.get('ko') or key
    for k, v in params.items():
        text = text.replace('{' + k + '}', str(v))
    return text


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