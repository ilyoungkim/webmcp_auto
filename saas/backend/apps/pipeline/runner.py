"""파이프라인 오케스트레이션 — worker가 호출."""
from __future__ import annotations

import html
import re

from django.conf import settings
from django.utils import timezone

from apps.catalogs.models import QuickMenu
from apps.projects.models import Project, TenantOrigin
from apps.widgets.generator import build_widget
from core.llm import GeminiError, ask_openrouter, resolve_openrouter_model
from core.origins import validate_crawl_url

from .crawler import crawl_many
from .models import GeneratedQnA, PipelineJob, SiteContent


def run_job(job: PipelineJob) -> None:
    project: Project = job.project
    try:
        job.status = 'running'
        job.attempt += 1
        job.locked_at = timezone.now()
        job.save(update_fields=['status', 'attempt', 'locked_at', 'updated_at'])

        # 1) 크롤 — sitemap.xml 기반 상위 페이지 다중 수집 또는 지정된 URL 목록 수집
        project.status, project.progress = 'crawling', 10
        project.status_message = '사이트맵 분석 중...'
        project.save(update_fields=['status', 'progress', 'status_message', 'updated_at'])
        validate_crawl_url(project.url)
        target_urls = job.selected_urls if (isinstance(job.selected_urls, list) and len(job.selected_urls) > 0) else None
        data = crawl_many(project.url, limit=10, target_urls=target_urls)
        page_urls = data.get('pages') or [project.url]
        page_titles = data.get('page_titles') or {}
        failed_pages = data.get('failed_pages') or []
        # 소스 URL + 제목을 함께 저장 (기존 문자열 목록과 호환)
        source_items = [{'url': u, 'title': page_titles.get(u, '')} for u in page_urls]
        failed_items = [{'url': f.get('url', ''), 'error': f.get('error', '')} for f in failed_pages]
        project.status, project.progress = 'crawling', 25
        if failed_items:
            project.status_message = f'페이지 {len(page_urls)}개 크롤 완료, {len(failed_items)}개 실패'
        else:
            project.status_message = f'페이지 {len(page_urls)}개 크롤 완료'
        project.save(update_fields=['status', 'progress', 'status_message', 'updated_at'])
        SiteContent.objects.filter(project=project).delete()
        SiteContent.objects.create(
            project=project, url=project.url,
            title=data['title'] or project.name,
            markdown=data['markdown'], char_count=len(data['markdown']),
            source_urls=source_items,
            failed_urls=failed_items,
        )
        _save_markdown_file(project, data['markdown'])

        # 2~4) 메뉴별 Q&A — 모든 메뉴를 한 번의 배치 호출로 생성 (개별 호출 제거)
        project.status, project.progress = 'generating', 30
        project.save(update_fields=['status', 'progress', 'updated_at'])
        menus = list(QuickMenu.objects.filter(domain_type=project.domain_type, enabled=True))
        qna_rows = []

        if menus:
            qna_rows = regenerate_qna(project, data['markdown'], menus)
            for i in range(len(menus)):
                project.progress = min(40 + i * 15 + 10, 89)
                project.save(update_fields=['progress', 'updated_at'])
        GeneratedQnA.objects.filter(project=project).delete()
        GeneratedQnA.objects.bulk_create(qna_rows)

        # 5) 위젯 생성 — 최신 생성 Q&A 질문을 퀵 메뉴에 반영
        project.progress = 90
        project.save(update_fields=['progress', 'updated_at'])
        build_widget(project, menus, data['markdown'], qna_rows=qna_rows)
        TenantOrigin.objects.get_or_create(origin=project.origin, defaults={'project': project})

        project.status, project.progress = 'completed', 100
        project.status_message = '완료'
        project.error = ''
        project.save(update_fields=['status', 'progress', 'status_message', 'error', 'updated_at'])
        job.status = 'completed'
        job.save(update_fields=['status', 'updated_at'])
    except Exception as e:  # noqa: BLE001
        project.status = 'failed'
        project.error = str(e)[:2000]
        project.save(update_fields=['status', 'error', 'updated_at'])
        job.status = 'failed'
        job.last_error = str(e)[:2000]
        job.save(update_fields=['status', 'last_error', 'updated_at'])


# 모델 답변에 잘못 포함된 마크다운 링크를 정제한다.
# 상대경로(/reserve/..)나 로컬 호스트(127.0.0.1 / localhost) 링크는
# 사용자가 입력한 도메인이 아닌 엉뚱한 주소로 오해석되므로 링크로 남기지 않는다.
_LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
_BAD_URL_RE = re.compile(r'^(?:(?:https?://)?(?:localhost|127\.0\.0\.1)(?:[:/]|$)|/[^/]|/)', re.I)


def _clean_answer_links(markdown: str) -> str:
    """답변에서 상대경로/로컬호스트 링크를 [텍스트](url) → 텍스트로 변환."""
    if not markdown:
        return markdown

    def _repl(m: re.Match) -> str:
        text, url = m.group(1), m.group(2).strip()
        if _BAD_URL_RE.match(url):
            return text.strip()
        return m.group(0)

    return _LINK_RE.sub(_repl, markdown)


# 생성된 답변에서 마크다운이 아닌 HTML 태그를 정제한다.
# - <br>, <br/>, <br /> → 줄바꿈(공백)
# - 그 외 태그(<strong>, <b>, <em>, <p>, <ul> 등) → 내용만 남기고 태그 제거
_BR_RE = re.compile(r'<br\s*/?>', re.I)
_HTML_TAG_RE = re.compile(r'<[^>]+>')


def _clean_answer_html(markdown: str) -> str:
    """답변에서 HTML 태그를 제거해 마크다운만 자연스럽게 표시되게 한다.

    - <br> 계열은 라인 단위로 처리한다.
      * 테이블 행(`| ... |`) 내부의 <br>는 **공백**으로 변환 (파이프 테이블 구조 보존)
      * 일반 줄의 <br>는 줄바꿈으로 변환
    - 그 외 태그(<strong>, <b>, <em>, <p>, <ul> 등) → 내용만 남기고 태그 제거
    """
    if not markdown:
        return markdown

    # 기타 HTML 태그 중 아직 남은 것을 먼저 제거하지 않고,
    # <br>부터 라인 단위 처리 후 나머지 태그를 제거한다.
    def _is_table_row(line: str) -> bool:
        s = line.strip()
        # 테이블 정렬 구분선(|---|) 또는 데이터 행(| ... |) 판별
        return s.startswith('|') or (s.count('|') >= 2 and '-|' in s)

    lines = markdown.split('\n')
    out: list[str] = []
    for line in lines:
        if _is_table_row(line):
            # 테이블 행: <br> → 공백 1개
            line = _BR_RE.sub(' ', line)
        else:
            # 일반 줄: <br> → 줄바꿈
            line = _BR_RE.sub('\n', line)
        out.append(line)
    text = '\n'.join(out)

    # 나머지 HTML 태그 제거
    text = _HTML_TAG_RE.sub('', text)
    # HTML 엔티티 디코딩(&#160;, &nbsp;, &amp;, &lt; 등) -> 실제 문자
    text = re.sub(r'&(?:#160|nbsp);', ' ', text, flags=re.I)
    text = html.unescape(text)
    # 줄바꿈이 연속으로 생성된 부분 정리 (빈 줄은 최대 2개 유지)
    text = re.sub(r'[ \t]+\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# 생성된 답변에서 마크다운이 아닌 HTML 태그를 정제한다.
# - <br>, <br/>, <br /> → 줄바꿈(공백)
# - 그 외 태그(<strong>, <b>, <em>, <p>, <ul> 등) → 내용만 남기고 태그 제거
_BR_RE = re.compile(r'<br\s*/?>', re.I)
_HTML_TAG_RE = re.compile(r'<[^>]+>')

# 안티봇 난독화된 이메일 등 잘못된 이메일을 걸러낸다.
# 사이트가 JS로 이메일을 렌더링하면 크롤 단계에서 '[email protected]' 같은
# 난독화 문자열이 남는다. 이를 그대로 답변에 넣으면 잘못된 정보가 되므로 제거/무효화.
_BAD_EMAIL_RE = re.compile(
    r'(?:\[email[^\]]*\]|[A-Za-z0-9._%+-]+@(?:\[email[^\]]*\]|protected|domain|sitename|example[^@\s]*))',
    re.I,
)
_OK_EMAIL_RE = re.compile(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')


def _clean_emails(markdown: str) -> str:
    """잘못된 이메일 난독화 문자열을 걸러낸다. 유효한 이메일만 유지."""
    if not markdown:
        return markdown

    # 난독화/걸리쉬 이메일 제거
    text = _BAD_EMAIL_RE.sub('', markdown)
    # 실제 값 없는 이메일 표기(****, 보호된 형태 등)가 들어간 어색한 문장 제거
    # 예: "**** 로 문의 주시면" 또는 "**** (사이트에 기재된 보호된 형태...)"
    text = re.sub(r'\*\*\*\*[^\n]*?[)）]?', '', text)
    text = re.sub(r'보호된 형태[^\n]*', '', text)
    # 이메일 헤더(📧 이메일 주소) 뒤에 실제 유효 이메일이 없으면 해당 블록 제거
    # → JS 난독화로 진짜 이메일이 없는데 '...로 보내주세요' 같은 빈 문단이 남는 것 방지
    text = _remove_empty_email_section(text)
    return text


# 이메일 섹션 제목 라인에 이모지 + '이메일' 단어가 함께 있는지 판별
_EMAIL_SECTION_RE = re.compile(r'[📧✉️💌@]')
_VALID_EMAIL_IN_TEXT_RE = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')


def _remove_empty_email_section(text: str) -> str:
    """이메일 섹션 제목 뒤에 실제 유효 이메일 값이 없으면 그 블록을 제거한다."""
    if not text:
        return text
    # 유효 이메일이 하나라도 있으면 전체를 유지 (이메일 안내가 유효)
    if _VALID_EMAIL_IN_TEXT_RE.search(text):
        return text

    # 유효 이메일이 전혀 없는 경우:
    # '이메일' 단어가 있는 줄(이메일 섹션 제목/본문)을 제거
    lines = text.split('\n')
    keep: list[str] = []
    skipping = False
    for ln in lines:
        s = ln.strip()
        # 이메일 섹션 시작: '이메일' 포함 + 이모지/칼럼 표시
        if '이메일' in s and _EMAIL_SECTION_RE.search(s):
            skipping = True
            continue
        # 다른 섹션이 시작되면 건너뛰기 중단 (이메일 본문이 끝났다고 봄)
        if skipping and s.startswith(('📞', '📍', '📅', '💡', '💼', '🗓️', '👤', '✉️', '📧', '→', '**', '#')):
            skipping = False
        if not skipping:
            keep.append(ln)
    return '\n'.join(keep).strip()


def _finalize_answer(markdown: str) -> str:
    """답변 최종 정제: 불량 링크 제거 + HTML 태그 정리 + 잘못된 이메일·이모지 제거."""
    text = _clean_answer_links(markdown)
    text = _clean_answer_html(text)
    text = _clean_emails(text)
    text = _strip_emoji(text)
    # 인사말 뒤에 섹션 제목(볼드)이 바로 붙으면 줄바꿈으로 분리해 읽기 좋게 한다.
    text = re.sub(r'(AI 비서입니다\.)\s*(\*\*[^*]+\*\*)', r'\1\n\n\2', text)
    # 불릿 내부에서 ' - '로 이어진 하위 항목을 줄바꿈으로 분리해 들여쓰기 정리.
    # 예: "- **석민쌤** - **전문 분야**: ..." → "- **석민쌤**\n  - **전문 분야**: ..."
    lines = text.split('\n')
    out: list[str] = []
    for ln in lines:
        if ln.startswith('- ') and ' - ' in ln:
            parts = ln.split(' - ')
            out.append(parts[0])
            for p in parts[1:]:
                out.append('  - ' + p)
        else:
            out.append(ln)
    text = '\n'.join(out)
    # 잘못된 이메일 제거 후 남는 공백 축소 (줄바꿈은 보존!)
    text = re.sub(r'[ \t]+\n', '\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


_EMOJI_RE = re.compile(
    '['
    '\U0001F300-\U0001F9FF'   # 기호/픽토그램
    '\U0001FA00-\U0001FA6F'   # 기호 확장
    '\U0001FA70-\U0001FAFF'
    '\U00002702-\U000027B0'   # 딩뱃
    '\U0001F000-\U0001F02F'
    '\U00002B00-\U00002BFF'
    '\U0000FE00-\U0000FE0F'   # 변형 선택자
    '\U0001F1E6-\U0001F1FF'   # 국기
    '\U0000200D'              # ZWJ
    '\U000020E3'              # 키캡
    ']+'
)


def _strip_emoji(text: str) -> str:
    """답변에서 이모지/이모티콘을 제거한다."""
    return _EMOJI_RE.sub('', text) if text else text


def _save_markdown_file(project: Project, markdown: str) -> None:
    """크롤 결과를 backend/crawled/project_<id>.md 로 저장. 실패해도 파이프라인은 계속."""
    try:
        from pathlib import Path
        out_dir = Path(settings.BASE_DIR) / 'crawled'
        out_dir.mkdir(parents=True, exist_ok=True)
        header = f'# {project.name}\n- source: {project.url}\n- project_id: {project.id}\n\n'
        (out_dir / f'project_{project.id}.md').write_text(header + markdown, encoding='utf-8')
    except Exception:  # noqa: BLE001
        pass


def _lang_gate(lang: str) -> str:
    """응답 언어 강제 지시문. en 사일로는 질문·답변 모두 영어로 생성한다."""
    if (lang or 'ko') == 'en':
        return (
            'LANGUAGE REQUIREMENT: Write EVERYTHING in English (questions AND answers).\n'
            'The site content may be in any language, but your output MUST be natural, professional English.\n\n'
        )
    return ''


def _batch_qna_prompt(markdown: str, project: Project, menus, questions_map: dict[str, str] | None = None) -> str:
    """여러 빠른메뉴의 질문/답변을 한 번의 API 호출로 생성하도록 하는 프롬프트.

    모델이 메뉴별로 질문을 추론하고, 각 질문에 대한 답변을
    명확한 마커(### [메뉴명]) 아래에 작성하도록 유도한다.
    """
    lang = (getattr(project, 'lang', '') or 'ko').lower()
    domain_hint = _domain_answer_hint(project, lang)
    menu_lines: list[str] = []
    for menu in menus:
        label = menu.label
        q = (questions_map or {}).get(label, '').strip()
        if q:
            menu_lines.append(f'- "{label}": 질문 = {q}')
        else:
            menu_lines.append(f'- "{label}": 힌트 = {menu.prompt_hint} (질문은 아래 규칙에 따라 생성)')
    menu_spec = '\n'.join(menu_lines)

    if lang == 'en':
        return (
            f'You are the AI assistant of {project.name}. Answer only based on the site content below.\n'
            f'Domain: {project.domain_type.name}\n'
            'Answer in English markdown.\n\n'
            'For each quick menu item below, first create **one active question** a real customer would ask, '
            'then write the answer to that question.\n'
            'Format each item exactly like this:\n\n'
            '### [menu label]\n'
            'Question: <one active question sentence>\n'
            'Answer: <English markdown answer>\n\n'
            'Quick menu items to write:\n'
            f'{menu_spec}\n\n'
            '【Question rules】\n'
            '- Avoid passive location questions like "where can I find". Ask **actively** about the actual information itself.\n'
            '- Do not ask about information the site does not have.\n\n'
            '【Answer format】\n'
            '- Never use tables. Use **bullet lists (- item)** instead. Start each section with a **bold title**.\n'
            '- **Never use emojis.** Separate paragraphs with blank lines.\n'
            '- Never output HTML tags (especially <br>).\n'
            f'- Start each answer with "Hello. This is the AI assistant of {project.name}."\n\n'
            '【Contact guidance】\n'
            '- Actively introduce real contact methods (phone, email, chat channel, booking links) found in the site content. Include markdown links as they appear.\n'
            '- **Never fabricate**: do not invent emails, phone numbers, addresses, or prices not on the site.\n\n'
            '【Never use negative expressions】\n'
            '- Never say "information is not available", "not provided", "not disclosed", "unknown". Guide positively with information that actually exists.\n\n'
            f'{domain_hint}'
            f'[Site content]\n{markdown}'
        )
    return (
        f'당신은 {project.name}의 AI 비서입니다. 아래 사이트 내용에 근거해서만 답하세요.\n'
        f'도메인: {project.domain_type.name}\n'
        '한국어 마크다운으로 답하세요.\n\n'
        '아래 각 빠른메뉴 항목에 대해, 고객이 실제로 궁금해할 만한 **능동적인 질문 한 문장**을 먼저 만들고, '
        '그 질문에 대한 답변을 작성하세요.\n'
        '각 항목은 반드시 다음 형식으로 구분해 출력하세요:\n\n'
        '### [메뉴명]\n'
        '질문: <능동적인 질문 한 문장>\n'
        '답변: <해당 질문에 대한 한국어 마크다운 답변>\n\n'
        '작성할 빠른메뉴 목록:\n'
        f'{menu_spec}\n\n'
        '【질문 생성 규칙】\n'
        '- "어디서 확인할 수 있나요", "어디에 있나요"처럼 정보의 위치를 묻는 수동적 질문은 피하세요.\n'
        '- 실제 정보 자체(연락처·전화번호·주소·서비스·내용 등)를 직접 묻는 **능동적** 질문을 만드세요.\n'
        '- 사이트에 없는 정보를 묻지 말고, 실제 있는 정보만 대상으로 하세요.\n\n'
        '【답변 형식】\n'
        '- 표(table)는 절대 사용하지 마세요. 대신 **불릿 목록(- 항목)**으로 정리하세요.\n'
        '- 여러 항목을 나열할 때는 각 항목을 **"- " 불릿**으로 시작하는 목록 형태로 작성하세요.\n'
        '- 각 섹션은 **굵게 제목**으로 시작하고, 그 아래 불릿 목록으로 내용을 정리하세요.\n'
        '- **이모지나 이모티콘을 절대 사용하지 마세요.**\n'
        '- 문단·항목 사이는 빈 줄로 구분해 띄어쓰기·줄내림이 자연스럽게 읽히도록 하세요.\n'
        '- HTML 태그(특히 <br>)를 절대 출력하지 마세요. 줄바꿈은 마크다운 빈 줄을 사용하세요.\n'
        '- 각 답변은 "안녕하세요. {project.name} AI 비서입니다."로 시작하세요.\n\n'
        '【연락·상담 방법 안내】\n'
        '- 사이트 내용에서 전화번호·이메일·카카오톡 채널·고객센터·예약/상담 신청 링크를 찾아 실제 있는 정보를 적극 안내하세요.\n'
        '- "카카오톡 상담", "카톡 예약", "고객센터", "무료 진단", "상담 예약" 문구가 있으면 그 이용 방법을 명확히 안내하세요.\n'
        '- 연결 링크([텍스트](URL))가 있으면 그대로 포함하세요.\n'
        '- **절대 지어내지 마세요**: 사이트에 없는 이메일·전화번호·주소·구체적 가격은 만들지 말고, 실제로 있는 연락 수단만 안내하세요.\n\n'
        '【부정 표현 절대 금지】\n'
        '- "정보가 없다", "제공되지 않습니다", "공개되지 않았습니다", "명시되어 있지 않습니다", "알 수 없습니다" 등 부정·소극 표현을 절대 출력하지 마세요.\n'
        '- 항상 긍정적으로, 사이트에 실제로 있는 정보 중심으로 안내하세요.\n'
        '- 전화번호·이메일이 따로 없어도 대체 연락 수단(카카오톡·채팅·예약폼 등)을 자신 있게 안내하세요.\n\n'
        f'{domain_hint}'
        f'[사이트 내용]\n{markdown}'
    )


def _question_prompt(markdown: str, project: Project, menu) -> str:
    """능동적이고 실제 고객이 궁금해할 만한 질문을 생성하도록 유도한다.

    메뉴의 목적(연락처 등)을 보고, '어디서 확인하나요' 같은 수동적 질문이 아니라
    해당 정보 자체를 요구하는 자연스러운 질문 한 문장을 만든다.
    """
    label = menu.label
    lang = (getattr(project, 'lang', '') or 'ko').lower()
    if lang == 'en':
        return (
            f'You are a customer of {project.name}. Based on the site content below, output **one specific question a real customer would ask** about the "{label}" menu.\n'
            f'Domain: {project.domain_type.name}\nhint: {menu.prompt_hint}\n\n'
            'Rules:\n'
            '- Do not make passive questions about where to find information. Ask **actively** about the actual information itself.\n'
            '- Do not ask about information that is not on the site.\n'
            '- Output **only one question sentence** without explanation.\n'
            '- The output MUST be in English.\n\n'
            f'[Site content]\n{markdown[:8000]}'
        )
    return (
        f'당신은 {project.name} 고객입니다. 아래 사이트 내용을 보고 '
        f'"{label}" 메뉴와 관련해 **고객이 실제로 궁금해할만한 구체적인 질문 한 문장**을 출력하세요.\n'
        f'도메인: {project.domain_type.name}\n힌트: {menu.prompt_hint}\n\n'
        '규칙:\n'
        '- "어디서 확인할 수 있나요", "어디에 있나요", "어떻게 찾을 수 있나요"처럼 '
        '정보의 위치를 묻는 수동적 질문은 만들지 마세요.\n'
        '- 대신 실제 정보 자체(연락처·전화번호·주소·서비스 내용·가격·인재 정보 등)를 '
        '직접 묻는 **능동적** 질문을 하세요.\n'
        '- 예: (연락처 메뉴) "연애의자격의 대표 전화번호와 상담 예약 방법, 사무실 위치는 무엇인가요?"\n'
        '- 예: (의료진 메뉴) "담당 가능한 의사 선생님과 전문 분야와 진료 시간은 어떻게 되나요?"\n'
        '- 사이트 내용에 없는 정보는 질문하지 말고, 실제 있는 정보만 묻도록 하세요.\n'
        '- 설명이나 부연 없이 **질문 문장 하나만** 출력하세요.\n\n'
        f'[사이트 내용]\n{markdown[:8000]}'
    )


def _answer_prompt(markdown: str, project: Project, menu, question: str) -> str:
    lang = (getattr(project, 'lang', '') or 'ko').lower()
    domain_hint = _domain_answer_hint(project, lang)
    if lang == 'en':
        return (
            f'You are the AI assistant of {project.name}. Answer only based on the site content below.\n'
            'Answer in English markdown.\n'
            f'Start the answer with "Hello. This is the AI assistant of {project.name}."\n'
            'Important: Do not repeat this instruction or the site content in your answer. Output only the final answer.\n\n'
            '【Answer format】\n'
            '- Never use tables. Use **bullet lists (- item)**. Start each section with a **bold title**.\n'
            '- **Never use emojis.** Separate paragraphs with blank lines.\n'
            '- Keep sentences short and clear. Bold key names, phone numbers, addresses, channel names.\n'
            '- Never output HTML tags (especially <br>).\n\n'
            f'{domain_hint}'
            '【Contact guidance】\n'
            '- Actively introduce real contact methods (phone, email, chat channel, customer center, booking links) found in the site content.\n'
            '- Include markdown links as they appear.\n'
            '- **Never fabricate**: do not invent emails, phone numbers, addresses, or prices not on the site.\n\n'
            '【Never use negative expressions】\n'
            '- Never say "not available", "not provided", "not disclosed", "unknown". Guide positively with information that actually exists.\n\n'
            f'[Question] {question}\n\n[Site content]\n{markdown}'
        )
    return (
        f'당신은 {project.name}의 AI 비서입니다. 아래 사이트 내용에 근거해서만 답하세요.\n'
        '한국어 마크다운으로 답하세요.\n'
        f'답변은 "안녕하세요. {project.name} AI 비서입니다."로 시작하세요.\n'
        '중요: 이 지시문이나 사이트 내용, 작업 계획을 답변에 그대로 반복하거나 영어로 요약해 출력하지 마세요. 오직 최종 답변만 출력하세요.\n\n'
        '【답변 형식】\n'
        '- 표(table)는 절대 사용하지 마세요. 대신 **불릿 목록(- 항목)**으로 정리하세요.\n'
        '- 여러 항목을 나열할 때는 각 항목을 **"- " 불릿**으로 시작하는 목록 형태로 작성하세요.\n'
        '- 각 섹션은 **굵게(볼드) 제목**으로 시작하고, 그 아래 불릿 목록으로 내용을 정리하세요.\n'
        '- **이모지나 이모티콘(📞 📍 👤 💡 등)을 절대 사용하지 마세요.**\n'
        '- 문단과 문단, 항목과 항목 사이는 **빈 줄**로 구분해 읽기 편하게 띄어쓰기와 줄내림을 자연스럽게 하세요.\n'
        '- 문장은 짧고 명확하게 끊어 쓰고, 핵심 명칭·전화번호·주소·채널명은 **굵게(볼드)**로 강조하세요.\n'
        '- HTML 태그(특히 <br>)를 절대 출력하지 마세요. 줄바꿈이 필요하면 마크다운의 빈 줄을 사용하세요.\n\n'
        f'{domain_hint}'
        '【연락·상담 방법 안내】\n'
        '- 사이트 내용에서 **전화번호, 이메일, 카카오톡 채널, 고객센터, 예약·상담 신청 링크**를 반드시 찾아 실제로 있는 정보를 적극적으로 안내하세요.\n'
        '- "카카오톡 상담", "카톡 예약", "고객센터", "무료 진단", "상담 예약" 등의 버튼·메뉴·문구가 보이면 그 구체적인 이용 방법을 안내하세요.\n'
        '- 예: 예약·상담은 카카오톡 채널을 통해 신청할 수 있다면, 그 채널명과 이용 절차를 명확히 적어주세요.\n'
        '- 연결 링크(마크다운 [텍스트](URL) 형식)가 있으면 그대로 포함하세요.\n'
        '- **절대 지어내지 마세요**: 사이트에 명시되지 않은 이메일 주소, 전화번호, 우편·도로명 주소, 구체적인 가격·비용은 만들거나 추측하지 마세요. 그런 값이 사이트 내용에 실제로 없으면 해당 항목은 아예 언급하지 말고, 확실히 있는 연락 수단(카카오톡·채팅·예약폼 등)만 안내하세요.\n\n'
        '【부정 표현 절대 금지】\n'
        '- "정보가 없다", "내용이 없다", "제공되지 않습니다", "공개되지 않았습니다", "명시되어 있지 않습니다", "확인되지 않습니다", "알 수 없습니다", "정보가 부족합니다", "모르겠습니다" 등 부정적·소극적 표현을 절대 출력하지 마세요.\n'
        '- 어떤 항목에도 "없다·미제공·미공개" 식의 표현을 쓰지 말고, 항상 **긍정적으로 실제 있는 정보 중심으로** 안내하세요.\n'
        '- 전화번호·이메일이 따로 없어도, 사이트에 있는 대체 연락 수단(카카오톡·채팅·예약폼 등)을 자신 있게 안내하세요.\n'
        '- 질문에 대답할 만한 정보가 있으면 그 정보를 충분히 활용해 답변을 채우세요.\n\n'
        f'[질문] {question}\n\n[사이트 내용]\n{markdown}'
    )


def _domain_answer_hint(project: Project, lang: str | None = None) -> str:
    """도메인별 답변 지침. 병원은 반드시 예약 방법·링크를 찾도록 강조한다."""
    dt = getattr(project, 'domain_type', None)
    code = dt.code if dt else ''
    lang = (lang or (getattr(project, 'lang', '') or 'ko')).lower()
    if code == 'hospital' or code.startswith('hospital_'):
        if lang == 'en':
            return (
                '【Hospital booking priority】\n'
                '- Always guide **how to book an appointment, checkup, or consultation** at the end of the answer.\n'
                '- Find real booking methods (online booking, phone) in the site content and introduce only the ones that exist.\n'
                '- Include booking links (markdown [text](URL)) or phone numbers when available.\n'
                '- Do not fabricate booking information that is not on the site.\n\n'
            )
        return (
            '【병원 예약 정보 우선 안내】\n'
            '- 답변 마지막에 **진료·검진·상담 예약 방법**을 반드시 안내하세요.\n'
            '- 사이트 내용에서 **네이버 예약**, **카카오톡 예약**, **온라인(홈페이지) 예약**, **전화 예약** 이 있는지 찾아 실제로 있는 예약 수단만 골라 안내하세요.\n'
            '- 각 예약 수단에 연결 링크(마크다운 [텍스트](URL) 형식)나 전화번호가 보이면 반드시 함께 포함하세요.\n'
            '- 사이트 내용에 "온라인예약", "카카오톡 상담", "전화상담예약" 등의 버튼/메뉴가 있으면 그 링크([텍스트](URL))를 그대로 답변에 포함하고 명시하세요.\n'
            '- 예약하기 (온라인): [온라인예약](연결URL) 형태로 실제 링크를 남기세요. 링크가 없으면 전화번호를 안내하세요.\n'
            '- 예약 관련 정보가 사이트에 없다면 "전화 예약 가능" 여부라도 안내하되, 없는 정보를 지어내지 마세요.\n\n'
        )
    return ''


_BATCH_SECTION_RE = re.compile(r'^#{1,4}\s*(.+?)\s*$', re.M)
# ko(질문/답변)와 en(Question/Answer) 배치 마커 모두 지원
_QUESTION_LINE_RE = re.compile(r'\**(?:질문|Question)\**\s*[:：]\s*(.+)', re.I)
_ANSWER_LINE_RE = re.compile(r'(?:^|\n)\s*\**(?:답변|Answer)\**\s*[:：]\s*', re.I)
_LEADING_MD_RE = re.compile(r'^[\s\*#\-—]+')


def _parse_batch_qna(text: str, menus) -> dict[str, dict]:
    """배치 응답에서 메뉴명 → {question, answer} 매핑을 추출한다.

    마커(### [메뉴명]) 아래 '질문:'/'답변:' 줄을 파싱한다.
    파싱 실패한 메뉴는 기본 질문과 빈 답변으로 처리해 개별 재시도 대상이 되게 한다.
    """
    result: dict[str, dict] = {}
    sections: dict[str, str] = {}
    markers = list(_BATCH_SECTION_RE.finditer(text))
    for i, m in enumerate(markers):
        title = m.group(1).strip()
        start = m.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        sections[title] = text[start:end].strip()

    for menu in menus:
        label = menu.label
        body = sections.get(label, '')
        # 마커 이름이 살짝 달라도(공백/괄호) 매칭 시도
        if not body:
            for title, content in sections.items():
                if label in title or title in label:
                    body = content
                    break
        question = ''
        answer = ''
        if body:
            qm = _QUESTION_LINE_RE.search(body)
            if qm:
                question = _LEADING_MD_RE.sub('', qm.group(1)).strip()
            am = _ANSWER_LINE_RE.search(body)
            if am:
                answer = body[am.end():].strip()
                # 선두에 남은 볼드 마커(** 등)나 공백 제거
                answer = _LEADING_MD_RE.sub('', answer)
                # 답변 끝에 섹션 구분선(---)이나 후속 마커가 붙지 않도록 정리
                answer = re.split(r'\n\s*-{3,}\s*\n|\n(?=#{1,4}\s)', answer)[0].strip()
                answer = re.sub(r'\s*-{3,}\s*$', '', answer).strip()
        result[label] = {
            'question': question or menu.question,
            'answer': answer,
        }
    return result


def regenerate_qna(project: Project, markdown: str, menus, questions_map: dict[str, str] | None = None) -> list[GeneratedQnA]:
    """이미 수집된 markdown을 기반으로 빠른메뉴 질문/답변을 재생성한다.

    - questions_map: menu_label → 사용자가 편집한 질문. 없으면 기존/자동 생성.
    - 재크롤링 없이 저장된 소스만으로 답변을 다시 만든다.
    - 모든 메뉴를 한 번의 배치 API 호출로 생성하며, 파싱 실패 메뉴만 개별 재시도한다.
    """
    qna_rows: list[GeneratedQnA] = []
    parsed: dict[str, dict] = {}
    # 언어 사일로 — 프로젝트의 언어로 엔진/프롬프트 언어가 결정된다
    lang = getattr(project, 'lang', '') or 'ko'
    try:
        batch_text = ask_openrouter(
            _batch_qna_prompt(markdown, project, menus, questions_map),
            temperature=0.3,
            lang=lang,
        )
        parsed = _parse_batch_qna(batch_text, menus)
    except GeminiError:
        parsed = {}

    for menu in menus:
        # 필수 메뉴("AI비서란?")는 DB에 저장된 공통 답변 사용 — LLM 호출 없이 안내
        if getattr(menu, 'is_required', False):
            qna_rows.append(GeneratedQnA(
                project=project, menu_label=menu.label,
                question=menu.question,
                answer_md=menu.answer_md or _required_menu_answer(project),
                model=resolve_openrouter_model(lang),
            ))
            continue

        meta = parsed.get(menu.label, {})
        question = (questions_map or {}).get(menu.label, '').strip() or meta.get('question', '').strip()
        answer = meta.get('answer', '').strip()
        existing = GeneratedQnA.objects.filter(project=project, menu_label=menu.label).first()

        if not question:
            question = existing.question if existing and existing.question else menu.question
        # 배치에서 질문/답변이 빠졌으면 개별 생성으로 보완
        if not question:
            try:
                question = ask_openrouter(_question_prompt(markdown, project, menu), temperature=0.3, lang=lang).strip().splitlines()[0]
            except GeminiError:
                question = existing.question if existing and existing.question else menu.question
        if not answer:
            if not question:
                question = existing.question if existing and existing.question else menu.question
            try:
                answer = ask_openrouter(_answer_prompt(markdown, project, menu, question), lang=lang)
            except GeminiError:
                answer = existing.answer_md if existing and existing.answer_md else ''

        answer = _finalize_answer(answer)
        qna_rows.append(GeneratedQnA(
            project=project, menu_label=menu.label,
            question=question, answer_md=answer, model=resolve_openrouter_model(lang),
        ))
    return qna_rows


def _required_menu_answer(project: Project) -> str:
    """필수 메뉴 'AI비서란?' 의 고정 답변 — AI비서 소개·사용 방법·문의 안내."""
    return (
        f'**AI비서란?**\n\n'
        f'AI비서는 {project.name} 홈페이지에 설치된 인공지능 상담 챗봇입니다. '
        '홈페이지의 정보를 학습하여 방문자에게 빠르고 정확한 답변을 제공합니다.\n\n'
        '**사용 방법**\n'
        '- 우하단 **AI** 버튼을 클릭하면 채팅창이 열립니다.\n'
        '- 빠른 메뉴(퀵 질문) 버튼을 누르면 자동으로 질문이 입력됩니다.\n'
        '- 직접 질문을 입력하거나 **🎤 음성 입력**으로 질문할 수 있습니다.\n'
        '- 답변은 수집된 홈페이지 정보를 기반으로 생성됩니다.\n\n'
        '**문의 안내**\n'
        '- 궁금한 점이 있으면 홈페이지의 **고객센터 Q&A**에 질문을 남겨주세요.\n'
        '- 또는 [AI 아카이브](https://ai-archive.co.kr/ko)에서 더 자세한 정보를 확인하실 수 있습니다.'
    )
