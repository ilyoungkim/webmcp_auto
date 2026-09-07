"""WebMCP 도구 유형 사전 — 빠른메뉴(중요 정보)를 개별 WebMCP 도구로 노출하기 위한 이름 매핑.

2계층 지식 구조의 Tier 1 지원:
- 중요 정보(연락처·영업시간·예약방법 등)는 빠른메뉴로 정의되며,
  이 모듈의 사전을 통해 표준화된 영문 도구명(get_contact_information 등)과
  설명(description)을 부여받아 개별 WebMCP 도구로 등록된다.
- 사전에 없는 일반 메뉴(병원정보·의료진 등)는 도메인 유형(category) 기반으로
  get_{category}_{slug(label)} 형태의 자동 도구명을 생성한다.
- Tier 2(전체 페이지 지식)는 get_page_answer(page, question) 도구로 별도 제공된다.
"""
from __future__ import annotations

import re

# ── Tier 1 핵심 정보 도구 사전 ─────────────────────────────────
# 키: (lang, 빠른메뉴 label). 값: (tool_name, description)
# 라벨은 seed_catalogs 의 빠른메뉴 label 과 정확히 일치해야 한다.
CORE_TOOL_DEFS: dict[tuple[str, str], tuple[str, str]] = {
    # ── 한국어(ko) ──
    ('ko', '연락처'): ('get_contact_information',
                       '대표 전화번호·이메일·카카오톡 채널 등 사이트의 주요 연락처 정보를 조회합니다.'),
    # ── 영어(en) ──
    ('en', 'Contact'): ('get_contact_information',
                        'Get the main contact information of this site: phone, email, chat channel, address.'),
}

# 라벨 키워드 → 표준 도구명 폴백 (위 사전에 없는 경우에도 핵심 정보는 자동 인식)
_KEYWORD_TOOL_MAP: list[tuple[re.Pattern, str, str, str]] = [
    # (패턴, ko/en 무관 도구명, ko 설명, en 설명)
    (re.compile(r'전화|contact|联系方式', re.I), 'get_contact_information',
     '사이트의 주요 연락처 정보를 조회합니다.',
     'Get the main contact information of this site.'),
    (re.compile(r'이메일|email', re.I), 'get_email_address',
     '사이트에 등록된 이메일 주소를 조회합니다.',
     'Get the email addresses listed on this site.'),
    (re.compile(r'오시는\s*길|찾아오는|위치|address|directions|location', re.I), 'get_location_and_directions',
     '주소와 오시는 길(대중교통·주차) 정보를 조회합니다.',
     'Get the address and directions to this site.'),
    (re.compile(r'영업시간|운영시간|진료시간|hours|opening', re.I), 'get_opening_hours',
     '영업·진료·운영 시간을 조회합니다.',
     'Get the business or operating hours.'),
    (re.compile(r'예약|booking|reservation|appointment', re.I), 'get_reservation_method',
     '예약·상담 신청 방법(온라인/전화/카카오톡)을 조회합니다.',
     'Get how to make a reservation or booking.'),
    (re.compile(r'가격|요금|비용|pricing|price|rates', re.I), 'get_pricing_information',
     '주요 가격·요금 정보를 조회합니다.',
     'Get pricing and fee information.'),
]


def _slug(text: str) -> str:
    """한글·특수문자를 제거한 영문 snake_case 슬러그. 결과가 비면 '' 반환."""
    s = re.sub(r'[^a-zA-Z0-9]+', '_', (text or '')).strip('_').lower()
    return s[:40]


def tool_for_menu(label: str, lang: str = 'ko', category: str = '') -> tuple[str, str]:
    """빠른메뉴 label 에 대해 (도구명, 설명) 을 반환한다.

    우선순위:
    1. CORE_TOOL_DEFS 정확 매칭 (수동 관리되는 Tier 1 핵심 도구)
    2. 키워드 패턴 매칭 (라벨에 포함된 핵심 정보 유형 자동 인식)
    3. 카테고리 + 라벨 슬러그 자동명 (일반 메뉴 — 예: hospital + Doctors → get_hospital_doctors)
    4. 최후 폴백: get_menu_<n> 형태는 위젯 JS 쪽에서 처리 (여기서는 '' 반환하지 않음)
    """
    key = (lang or 'ko', (label or '').strip())
    if key in CORE_TOOL_DEFS:
        return CORE_TOOL_DEFS[key]

    for pattern, name, desc_ko, desc_en in _KEYWORD_TOOL_MAP:
        if pattern.search(label or ''):
            return (name, desc_en if (lang or 'ko') == 'en' else desc_ko)

    slug = _slug(label)
    cat = _slug(category) or 'site'
    if slug:
        name = f'get_{cat}_{slug}' if cat != 'site' else f'get_{slug}'
        desc = (f'Answer common questions about "{label}" of this site.'
                if (lang or 'ko') == 'en'
                else f'이 사이트의 "{label}" 관련 정보를 안내합니다.')
        return (name[:64], desc)

    # 한글 전용 라벨 등 슬러그 생성 불가 → 호출부(JS)의 폴백에 맡기되 이름은 제안
    name = f'get_{cat}_menu'
    desc = (f'Information about {label}.' if (lang or 'ko') == 'en'
            else f'{label} 정보를 안내합니다.')
    return (name, desc)


def is_core_tool(name: str) -> bool:
    """표준 Tier 1 핵심 도구인지 판별 (위젯 config 의 tier 표시용)."""
    return name in {t for t, _ in CORE_TOOL_DEFS.values()}
