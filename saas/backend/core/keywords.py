"""사일로 언어별 질문 키워드 설정 로더.

`core/keywords.yaml`을 읽어 언어별 (정규식, 불용어, 핵심어, 최대 개수)를 제공한다.
PyYAML 없이 표준 라이브러리만으로 파싱하므로 requirements 추가가 필요 없다.

재사용 방법:
    from core.keywords import keyword_rules, question_keywords

    rules = keyword_rules()            # {'en': {...}, 'ko': {...}}
    kws = question_keywords('예약 어떻게 해요?', 'ko')  # ['예약', '해요']
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

YAML_PATH = Path(__file__).with_name('keywords.yaml')

# YAML 파싱 실패 시 폴백 — 기존 하드코딩 값과 동일
_FALLBACK = {
    'en': {
        'pattern': r'[A-Za-z]{3,}',
        'max_keywords': 6,
        'stopwords': frozenset('''
            a an the and or but of to in on at for with by from as is are was were be been being
            do does did will would can could should may might must shall have has had having
            this that these those it its it's i you he she we they me him her us them my your his
            our their what which who whom whose when where why how many much more most other
            some such no not only own same so than too very just about into over after before
            between through during each few hello hi thanks thank please tell give show find get
            '''.split()),
        'keepwords': frozenset(
            ['address', 'phone', 'price', 'hours', 'location', 'booking', 'contact']),
    },
    'ko': {
        'pattern': r'[가-힣]{2,}',
        'max_keywords': 6,
        'stopwords': frozenset('''
            이 그 저 것 거 게 건 를 을 가 이 에 게 에서 로 으로 와 과 하고 한 할 함 것들 수 있 없
            네 요 죠 까 뭐 뭔 어떻게 어디 언제 누구 무엇 무슨 어떤 왜 해 주세요 알려
            주세요 있나요 없나요 합니까 입니까
            '''.split()),
        'keepwords': frozenset(
            ['문의', '상담', '예약', '전화', '번호', '주소', '위치', '시간', '비용', '가격']),
    },
}


def _parse_simple_yaml(text: str) -> dict:
    """keywords.yaml 전용 미니 파서.

    지원하는 구조: 최상위 언어 키 → pattern/max_keywords/stopwords/keepwords.
    리스트 항목은 '- ' 접두 줄, 스칼라는 'key: value' 줄만 처리한다.
    따옴표로 감싼 값("it's", "[A-Za-z]{3,}")의 따옴표를 벗긴다.
    """
    data: dict[str, dict] = {}
    lang: str | None = None
    section: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith('#'):
            continue
        indent = len(line) - len(line.lstrip(' '))
        stripped = line.strip()
        if indent == 0 and stripped.endswith(':'):
            lang = stripped[:-1]
            data[lang] = {'stopwords': [], 'keepwords': []}
            section = None
        elif indent == 2 and lang:
            if stripped.startswith('- '):
                value = stripped[2:].strip().strip('"').strip("'")
                if section in ('stopwords', 'keepwords'):
                    data[lang][section].append(value)
            elif ':' in stripped:
                key, _, value = stripped.partition(':')
                key, value = key.strip(), value.strip().strip('"').strip("'")
                if key in ('stopwords', 'keepwords'):
                    section = key
                elif key == 'pattern':
                    data[lang]['pattern'] = value
                    section = None
                elif key == 'max_keywords':
                    data[lang]['max_keywords'] = int(value)
                    section = None
                else:
                    section = None
        elif indent == 4 and lang and stripped.startswith('- '):
            value = stripped[2:].strip().strip('"').strip("'")
            if section in ('stopwords', 'keepwords'):
                data[lang][section].append(value)
    return data


@lru_cache(maxsize=1)
def keyword_rules() -> dict:
    """언어별 키워드 규칙 dict. YAML이 없거나 깨지면 내장 기본값으로 폴백."""
    rules: dict[str, dict] = {}
    try:
        text = YAML_PATH.read_text(encoding='utf-8')
        parsed = _parse_simple_yaml(text)
        for lang, cfg in parsed.items():
            rules[lang] = {
                'pattern': cfg.get('pattern') or _FALLBACK.get(lang, {}).get('pattern', r'\w+'),
                'max_keywords': int(cfg.get('max_keywords') or 6),
                'stopwords': frozenset(cfg.get('stopwords') or ()),
                'keepwords': frozenset(cfg.get('keepwords') or ()),
            }
    except Exception:  # noqa: BLE001 — YAML 문제 시 내장 기본값 사용
        pass
    if not rules:
        return {k: dict(v) for k, v in _FALLBACK.items()}
    for lang, fb in _FALLBACK.items():
        rules.setdefault(lang, dict(fb))
    return rules


def reload_keywords() -> dict:
    """YAML을 다시 읽는다 (편집 후 반영용)."""
    keyword_rules.cache_clear()
    return keyword_rules()


def question_keywords(question: str, lang: str) -> list[str]:
    """사일로 언어에 맞는 규칙으로 검색용 핵심 키워드 추출.

    - keepwords에 있으면 stopwords에 있어도 키워드로 유지한다.
    - 미지정 언어는 영·한 순서로 결합한다.
    """
    rules = keyword_rules()
    lang = (lang or '').lower()
    langs = [lang] if lang in rules else ['en', 'ko']
    seen: set[str] = set()
    out: list[str] = []
    for lg in langs:
        cfg = rules.get(lg)
        if not cfg:
            continue
        stopwords = cfg['stopwords'] - cfg['keepwords']
        for w in re.findall(cfg['pattern'], question or ''):
            lw = w.lower()
            if lw in stopwords or lw in seen:
                continue
            seen.add(lw)
            out.append(w)
            if len(out) >= cfg['max_keywords']:
                return out
    return out
