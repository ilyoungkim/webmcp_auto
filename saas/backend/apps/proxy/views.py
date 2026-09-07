"""POST /api/chat/ — Origin+publicId 인증, 서버가 system_prompt 부착."""
from __future__ import annotations

import difflib
import json
import time

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.pipeline.models import GeneratedQnA, PageKnowledge
from apps.projects.models import Project
from apps.widgets.models import Widget
from core.langsilo import msg
from core.llm import ask, strip_instruction_echo

from .models import RequestLog
from .quotas import monthly_ok, per_minute_ok, record


def _client_ip(request):
    from core.clientip import client_ip
    return client_ip(request)


def _log(request, verdict, reason='', public_id=''):
    RequestLog.objects.create(
        origin=request.headers.get('origin', '') or '',
        public_id=public_id,
        ip=_client_ip(request),
        path=request.path,
        verdict=verdict,
        reason=reason[:255],
    )


@csrf_exempt
@require_POST
def chat(request):
    origin = request.headers.get('origin') or ''
    try:
        body = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        _log(request, 'blocked_401', 'bad_json')
        return JsonResponse({'error': msg('common.badRequest')}, status=401)

    question = (body.get('question') or '').strip()
    public_id = (body.get('publicId') or '').strip()
    memory = (body.get('memory') or '').strip()  # 이전 대화 기억 컨텍스트(선택)
    if not question or not public_id:
        _log(request, 'blocked_401', 'missing_fields', public_id)
        return JsonResponse({'error': msg('proxy.questionRequired')}, status=401)

    project = Project.objects.filter(public_id=public_id).first()
    widget = Widget.current(project) if project else None
    if project is None or widget is None:
        _log(request, 'blocked_403', 'unknown_public_id', public_id)
        return JsonResponse({'error': msg('proxy.widgetNotRegistered')}, status=403)

    # 사용중지된 프로젝트는 위젯 서빙 중지
    if not project.enabled:
        _log(request, 'blocked_403', 'project_disabled', public_id)
        return JsonResponse({'error': msg('proxy.widgetDisabled')}, status=403)

    # 인증: Origin 화이트리스트 또는 (세션 + 소유권/미리보기)
    allowed_origin = any(
        o.enabled and o.origin == origin for o in project.origins.all()
    )
    session_owner = (
        request.user.is_authenticated
        and (project.user_id == request.user.id or request.user.role == 'admin')
    )
    # 오리진 자동 학습 — 소유자/관리자가 자기 위젯을 설치 사이트에서 시험하면
    # 그 오리진을 화이트리스트에 자동 등록한다. 이후 익명 방문자도 403 없이 사용 가능.
    # (스크린샷 사례: 콘솔에서 다운로드한 위젯을 다른 도메인에 설치하면
    #  프로젝트 URL과 달라 403이 반복되는 문제의 근본 해소)
    if session_owner and origin and not allowed_origin:
        from apps.projects.models import TenantOrigin
        from core.origins import normalize_origin
        normalized = normalize_origin(origin)
        if TenantOrigin.objects.filter(origin=normalized).exists():
            # 다른 프로젝트가 점유 중인 오리진 — 자동 등록 불가
            pass
        else:
            TenantOrigin.objects.get_or_create(origin=normalized, defaults={'project': project})
            allowed_origin = True
            _log(request, 'ok', f'origin_learned:{normalized[:80]}', public_id)
    if not allowed_origin and not session_owner:
        _log(request, 'blocked_403', 'origin_not_allowed', public_id)
        return JsonResponse({'error': msg('proxy.domainNotAllowed')}, status=403)

    if not session_owner:
        if not per_minute_ok(None, project) or not monthly_ok(project.user):
            _log(request, 'blocked_429', 'quota', public_id)
            return JsonResponse({'error': msg('proxy.rateLimited')}, status=429)

    # 저장된 Q&A 우선 매칭 (토큰 절약) — 빠른메뉴와 거의 동일한 질문만 DB 답변 반환
    cached = _match_cached_qna(project, question)
    if cached:
        # AI가 생각하는 듯한 자연스러운 UX를 위해 짧은 지연 후 반환
        time.sleep(2)
        cleaned = strip_instruction_echo(cached.answer_md) or cached.answer_md
        record(project.user, project, 'chat')
        _log(request, 'ok', 'cached_qna', public_id)
        return _gemini_shape(cleaned)

    # 언어 사일로 — en 위젯은 영어 라벨 사용 (한국어 라벨이 언어 혼용 유도 방지)
    project_lang = (getattr(project, 'lang', '') or 'ko').lower()
    user_turn = 'User question:' if project_lang == 'en' else '사용자 질문'
    prompt = f"{widget.system_prompt}\n\n{memory}\n{user_turn}: {question}"

    # 관리자 입력 페이지별 추가 지식 — 자유 질문 답변 강화 (사이트에 없거나 크롤이 놓친 최신 정보)
    extra_ctx = _extra_knowledge_context(project, project_lang)
    if extra_ctx:
        prompt = f"{widget.system_prompt}\n\n{extra_ctx}\n{memory}\n{user_turn}: {question}"
    # 질문 키워드 관련 페이지 원문 — 질문마다 다른 컨텍스트로 맞춤 답변 유도
    page_ctx = _search_pages_by_keywords(project, question, project_lang)
    if page_ctx:
        prompt = f"{widget.system_prompt}\n\n{page_ctx}\n{memory}\n{user_turn}: {question}"
        if extra_ctx:
            prompt = f"{widget.system_prompt}\n\n{extra_ctx}\n\n{page_ctx}\n{memory}\n{user_turn}: {question}"
    try:
        # 실시간 채팅: 응답 토큰 상한과 짧은 타임아웃으로 지연 최소화
        # 테넌트(project)별 Gemini 키/모델 설정을 우선 적용하고,
        # 언어 사일로 전용 엔진(GEMINI_API_KEY_EN 등)을 함께 반영한다.
        answer = ask(prompt, max_tokens=1024, timeout=30.0, project=project, lang=project_lang)
    except Exception as e:  # noqa: BLE001
        _log(request, 'blocked_401', f'llm_error:{str(e)[:120]}', public_id)
        return JsonResponse({'error': msg('proxy.aiFailed')}, status=502)
    answer = strip_instruction_echo(answer) or answer

    record(project.user, project, 'chat')
    _log(request, 'ok', '', public_id)
    return _gemini_shape(answer)


@csrf_exempt
@require_POST
def chat_error_report(request):
    """위젯에서 '오류 신고하기' 클릭 시 호출. 오류 내용을 DB에 저장한다."""
    from .models import ChatErrorReport

    origin = request.headers.get('origin') or ''
    try:
        body = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': msg('common.badRequest')}, status=400)

    public_id = (body.get('publicId') or '').strip()
    question = (body.get('question') or '').strip()
    error_message = (body.get('errorMessage') or '').strip()
    error_detail = (body.get('errorDetail') or '').strip()

    if not error_message:
        return JsonResponse({'error': msg('proxy.errorMessageRequired')}, status=400)

    project = Project.objects.filter(public_id=public_id).first() if public_id else None
    ChatErrorReport.objects.create(
        project=project,
        public_id=public_id,
        origin=origin,
        question=question[:2000],
        error_message=error_message[:2000],
        error_detail=error_detail[:8000],
        ip=_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:512],
    )
    return JsonResponse({'ok': True})


@csrf_exempt
@require_POST
def page_answer(request):
    """POST /api/chat/page-answer/ — Tier 2 페이지별 검색 답변.

    body: {publicId, page, question}
    - page 는 크롤 시 저장된 PageKnowledge 의 url 또는 title 로 부분 일치 탐색.
    - 해당 페이지 원문 마크다운만을 컨텍스트로 사용해 답변을 생성한다.
      (전체 사이트 요약이 아닌 페이지 단위 지식 검색)
    - 인증·쿼터는 /api/chat/ 과 동일한 정책을 적용한다.
    """
    origin = request.headers.get('origin') or ''
    try:
        body = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        _log(request, 'blocked_401', 'bad_json')
        return JsonResponse({'error': msg('common.badRequest')}, status=401)

    question = (body.get('question') or '').strip()
    page = (body.get('page') or '').strip()
    public_id = (body.get('publicId') or '').strip()
    if not question or not public_id:
        _log(request, 'blocked_401', 'missing_fields', public_id)
        return JsonResponse({'error': msg('proxy.questionRequired')}, status=401)

    project = Project.objects.filter(public_id=public_id).first()
    widget = Widget.current(project) if project else None
    if project is None or widget is None:
        _log(request, 'blocked_403', 'unknown_public_id', public_id)
        return JsonResponse({'error': msg('proxy.widgetNotRegistered')}, status=403)
    if not project.enabled:
        _log(request, 'blocked_403', 'project_disabled', public_id)
        return JsonResponse({'error': msg('proxy.widgetDisabled')}, status=403)

    allowed_origin = any(
        o.enabled and o.origin == origin for o in project.origins.all()
    )
    session_owner = (
        request.user.is_authenticated
        and (project.user_id == request.user.id or request.user.role == 'admin')
    )
    if not allowed_origin and not session_owner:
        _log(request, 'blocked_403', 'origin_not_allowed', public_id)
        return JsonResponse({'error': msg('proxy.domainNotAllowed')}, status=403)
    if not session_owner:
        if not per_minute_ok(None, project) or not monthly_ok(project.user):
            _log(request, 'blocked_429', 'quota', public_id)
            return JsonResponse({'error': msg('proxy.rateLimited')}, status=429)

    from apps.pipeline.models import PageKnowledge

    pk_row = _find_page_knowledge(project, page)
    if pk_row is None:
        # 페이지를 특정할 수 없으면 일반 채팅 경로로 위임 (자유 질문으로 처리)
        record(project.user, project, 'chat')
        _log(request, 'ok', 'page_answer_fallback_chat', public_id)
        prompt = f"{widget.system_prompt}\n\nUser question: {question}" \
            if (getattr(project, 'lang', '') or 'ko').lower() == 'en' \
            else f"{widget.system_prompt}\n\n사용자 질문: {question}"
        try:
            answer = ask(prompt, max_tokens=1024, timeout=30.0, project=project,
                         lang=(getattr(project, 'lang', '') or 'ko').lower())
        except Exception as e:  # noqa: BLE001
            _log(request, 'blocked_401', f'llm_error:{str(e)[:120]}', public_id)
            return JsonResponse({'error': msg('proxy.aiFailed')}, status=502)
        return _gemini_shape(strip_instruction_echo(answer) or answer)

    project_lang = (getattr(project, 'lang', '') or 'ko').lower()
    page_prompt = _page_answer_prompt(project, pk_row, question, project_lang)
    try:
        answer = ask(page_prompt, max_tokens=1024, timeout=30.0, project=project, lang=project_lang)
    except Exception as e:  # noqa: BLE001
        _log(request, 'blocked_401', f'llm_error:{str(e)[:120]}', public_id)
        return JsonResponse({'error': msg('proxy.aiFailed')}, status=502)
    answer = strip_instruction_echo(answer) or answer

    record(project.user, project, 'chat')
    _log(request, 'ok', f'page_answer:{pk_row.url[:80]}', public_id)
    return _gemini_shape(answer)


# 질문 키워드 추출 규칙은 core/keywords.yaml 에서 관리한다.
# (언어별 편집·재사용 가능. YAML이 없거나 깨지면 내장 기본값으로 폴백)
# 구버전 호환: 외부에서 import 하던 _question_keywords 를 유지한다.
def _question_keywords(question: str, lang: str) -> list[str]:
    """사일로 언어에 맞는 규칙으로 검색용 핵심 키워드 추출.

    실제 규칙은 core.keywords.question_keywords 에 위임한다.
    """
    from core.keywords import question_keywords
    return question_keywords(question, lang)


def _search_pages_by_keywords(project, question: str, lang: str, limit: int = 2) -> str:
    """자유 질문의 키워드로 PageKnowledge를 검색해 관련 페이지 원문을 반환한다.

    질문마다 다른 페이지가 컨텍스트에 들어가므로, 비슷한 질문도 질문별 맞춤
    답변을 생성한다. ("orthodontic doctor address?" vs "phone number?"가 같은
    답을 내던 문제의 해소 — 관련 페이지 원문이 다르면 답변도 달라진다.)
    관련 페이지가 없으면 '' (프롬프트 불변). 총 4,000자 상한.
    """
    from django.db.models import Q

    keywords = _question_keywords(question, lang)
    if not keywords:
        return ''
    query = Q()
    for kw in keywords:
        query |= Q(markdown__icontains=kw) | Q(title__icontains=kw) | Q(url__icontains=kw)
    rows = (
        PageKnowledge.objects.filter(project=project).filter(query).order_by('id')[:limit]
    )
    if not rows:
        return ''
    budget = 4000
    parts: list[str] = []
    for r in rows:
        if budget <= 0:
            break
        snippet = (r.markdown or '').strip()[:2000]
        label = r.title or r.url
        parts.append(f'- [{label}]\n{snippet}')
        budget -= len(snippet)
    header = (
        '[Related site pages for this question — answer based on these when relevant]'
        if lang == 'en' else
        '[이 질문과 관련된 사이트 페이지 — 관련 있으면 답변에 반영하세요]'
    )
    return f'{header}\n\n' + '\n\n'.join(parts)


def _extra_knowledge_context(project, lang: str) -> str:
    """관리자가 입력한 페이지별 추가 지식을 자유 질문 컨텍스트 블록으로 모은다.

    토큰 절약: 추가 지식이 있는 페이지만, 총 6,000자 상한(페이지당 앞부분 잘림).
    없으면 '' 반환 (프롬프트 불변).
    """
    from apps.pipeline.models import PageKnowledge

    rows = PageKnowledge.objects.filter(project=project).exclude(extra_md='').order_by('id')
    if not rows.exists():
        return ''
    budget = 6000
    parts: list[str] = []
    for r in rows:
        if budget <= 0:
            break
        snippet = (r.extra_md or '').strip()[:1500]
        label = r.title or r.url
        parts.append(f'- [{label}]\n{snippet}')
        budget -= len(snippet)
    header = (
        '[Extra knowledge provided by the site owner — newer than crawled content, use it when relevant]'
        if lang == 'en' else
        '[사이트 운영자가 입력한 추가 지식 — 크롤링 내용보다 최신이며 관련 있으면 답변에 반영하세요]'
    )
    return f'{header}\n\n' + '\n\n'.join(parts)


def _find_page_knowledge(project, page: str):
    """page 문자열(url 또는 title)로 PageKnowledge 행을 찾는다.

    - 정확 일치(url) → title 정확 일치 → url/title 부분 일치 순.
    - page 가 비면 None (호출부에서 자유 질문으로 위임).
    """
    from apps.pipeline.models import PageKnowledge

    key = (page or '').strip().rstrip('/')
    if not key:
        return None
    qs = PageKnowledge.objects.filter(project=project)
    row = qs.filter(url=key).first() or qs.filter(url=f'{key}/').first()
    if row:
        return row
    row = qs.filter(title=key).first()
    if row:
        return row
    from django.db.models import Q
    return qs.filter(Q(url__icontains=key) | Q(title__icontains=key)).first()


def _page_answer_prompt(project, pk_row, question: str, lang: str) -> str:
    """페이지 원문 전용 컨텍스트로 답하는 프롬프트 (Tier 2).

    pk_row.knowledge_text() = 크롤 원문 + 관리자 입력 추가 지식(extra_md).
    추가 지식이 있으면 사이트 운영자가 최신 정보로 갱신한 것이므로 우선한다.
    """
    domain_name = getattr(getattr(project, 'domain_type', None), 'name', '')
    page_label = pk_row.title or pk_row.url
    content = pk_row.knowledge_text()[:14000]
    extra_note = (
        'If the page contains a "[Extra info by site owner]" section, it is newer than the crawled text and takes precedence.\n'
        if (pk_row.extra_md or '').strip() else ''
    )
    if lang == 'en':
        return (
            f'You are the AI assistant of {project.name}. Answer ONLY based on the content of the page "{page_label}" below.\n'
            'If the answer is inside this page, answer concisely in English markdown starting with '
            f'"Hello. This is the AI assistant of {project.name}." Never fabricate information that is not in the page.\n'
            f'{extra_note}'
            'Never use tables, emojis, or HTML tags. Use bullet lists and bold section titles.\n\n'
            f'[Page: {pk_row.url}]\n{content}\n\n[Question] {question}'
        )
    return (
        f'당신은 {project.name}의 AI 비서입니다. 아래 "{page_label}" 페이지 내용에 근거해서만 답하세요.\n'
        f'답변은 "안녕하세요. {project.name} AI 비서입니다."로 시작하고 한국어 마크다운으로 간결히 답하세요.\n'
        '표·이모지·HTML 태그(<br> 등)는 절대 사용하지 마세요. 불릿 목록과 굵은 섹션 제목을 사용하세요.\n'
        '페이지에 없는 정보를 지어내지 마세요.\n'
        + ('\n'.join([
            '※ "[관리자 제공 추가 정보]" 섹션이 있으면 크롤 원문보다 최신 정보이므로 우선 반영하세요.',
        ]) if (pk_row.extra_md or '').strip() else '')
        + f'\n\n[도메인: {domain_name}]\n'
        f'[페이지: {pk_row.url}]\n{content}\n\n[질문] {question}'
    )


# 빠른메뉴 질문과의 유사도 임계값 — 이 이상만 DB 답변을 사용.
# 2026-09-07 실측: 진짜 같은 의도는 0.71~0.76, 다른 의도는 0.6 이하로 갈림.
# 0.6은 짧은 질문에서 우연히 넘어갈 수 있어 0.75로 상향.
_QNA_SIM_THRESHOLD = 0.75

# 짧은 질문은 문자 단위 유사도가 부풀려지므로 캐시 대상에서 제외한다.
# ("Hello", "Thanks" 같은 인사는 Gemini가 자연스럽게 응대)
_QNA_MIN_LEN = 15


def _match_cached_qna(project, question: str):
    """저장된 Q&A 중 빠른메뉴 질문과 '거의 동일한' 답변을 찾는다. 없으면 None.

    - 완전 일치(빠른메뉴 버튼 클릭)는 항상 DB 답변 반환 (토큰 절약).
    - 그 외는 공백 정규화 후 difflib 유사도가 임계값(0.75) 이상일 때만 반환.
    - 짧은 질문(15자 미만)은 유사도가 부풀려지므로 Gemini로 처리.
    - "점도빼주나요?"처럼 빠른메뉴와 무관한 질문은 유사도가 낮아
      Gemini로 처리된다 (오탐 방지).
    """
    q = ' '.join(question.split()).strip()
    if not q:
        return None

    rows = list(GeneratedQnA.objects.filter(project=project))
    best: tuple[float, object] | None = None
    for r in rows:
        stored = ' '.join(r.question.split()).strip()
        if not stored:
            continue
        if q == stored:
            return r  # 빠른메뉴 버튼 클릭 — 완전 일치는 항상 캐시
        ratio = difflib.SequenceMatcher(None, q, stored).ratio()
        if best is None or ratio > best[0]:
            best = (ratio, r)

    if len(q) < _QNA_MIN_LEN:
        return None
    if best and best[0] >= _QNA_SIM_THRESHOLD:
        return best[1]
    return None


def _gemini_shape(text: str) -> HttpResponse:
    """기존 위젯(webmcp.js)이 파싱하는 Gemini 응답 형태 유지."""
    return JsonResponse({
        'candidates': [{'content': {'parts': [{'text': text}]}}]
    })
