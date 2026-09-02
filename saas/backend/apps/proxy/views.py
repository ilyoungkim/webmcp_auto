"""POST /api/chat/ — Origin+publicId 인증, 서버가 system_prompt 부착."""
from __future__ import annotations

import difflib
import json
import time

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.pipeline.models import GeneratedQnA
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


# 빠른메뉴 질문과의 유사도 임계값 — 이 이상만 DB 답변을 사용
_QNA_SIM_THRESHOLD = 0.6


def _match_cached_qna(project, question: str):
    """저장된 Q&A 중 빠른메뉴 질문과 '거의 동일한' 답변을 찾는다. 없으면 None.

    - 공백 정규화 후 difflib 유사도 계산.
    - 유사도가 임계값(0.6) 이상인 경우에만 DB 답변 반환.
    - "점도빼주나요?"처럼 빠른메뉴와 무관한 질문은 유사도가 낮아
      Gemini로 처리된다 (오탐 방지).
    """
    from apps.pipeline.models import GeneratedQnA

    q = ' '.join(question.split()).strip()
    if not q:
        return None

    rows = list(GeneratedQnA.objects.filter(project=project))
    best: tuple[float, object] | None = None
    for r in rows:
        stored = ' '.join(r.question.split()).strip()
        if not stored:
            continue
        ratio = difflib.SequenceMatcher(None, q, stored).ratio()
        if best is None or ratio > best[0]:
            best = (ratio, r)

    if best and best[0] >= _QNA_SIM_THRESHOLD:
        return best[1]
    return None


def _gemini_shape(text: str) -> HttpResponse:
    """기존 위젯(webmcp.js)이 파싱하는 Gemini 응답 형태 유지."""
    return JsonResponse({
        'candidates': [{'content': {'parts': [{'text': text}]}}]
    })
