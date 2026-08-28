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
from core.llm import ask, strip_instruction_echo

from .models import RequestLog
from .quotas import monthly_ok, per_minute_ok, record


def _client_ip(request):
    fwd = request.META.get('HTTP_X_FORWARDED_FOR')
    return (fwd.split(',')[0].strip() if fwd else request.META.get('REMOTE_ADDR')) or ''


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
        return JsonResponse({'error': '잘못된 요청'}, status=401)

    question = (body.get('question') or '').strip()
    public_id = (body.get('publicId') or '').strip()
    memory = (body.get('memory') or '').strip()  # 이전 대화 기억 컨텍스트(선택)
    if not question or not public_id:
        _log(request, 'blocked_401', 'missing_fields', public_id)
        return JsonResponse({'error': 'question/publicId 필요'}, status=401)

    project = Project.objects.filter(public_id=public_id).first()
    widget = Widget.current(project) if project else None
    if project is None or widget is None:
        _log(request, 'blocked_403', 'unknown_public_id', public_id)
        return JsonResponse({'error': '등록되지 않은 위젯'}, status=403)

    # 사용중지된 프로젝트는 위젯 서빙 중지
    if not project.enabled:
        _log(request, 'blocked_403', 'project_disabled', public_id)
        return JsonResponse({'error': '사용이 중지된 위젯입니다.'}, status=403)

    # 인증: Origin 화이트리스트 또는 (세션 + 소유권/미리보기)
    allowed_origin = any(
        o.enabled and o.origin == origin for o in project.origins.all()
    )
    session_owner = (
        request.user.is_authenticated
        and (project.user_id == request.user.id or request.user.role == 'admin')
    )
    if not allowed_origin and not session_owner:
        _log(request, 'blocked_403', 'origin_not_allowed', public_id)
        return JsonResponse({'error': '허용되지 않은 도메인'}, status=403)

    if not session_owner:
        if not per_minute_ok(None, project) or not monthly_ok(project.user):
            _log(request, 'blocked_429', 'quota', public_id)
            return JsonResponse({'error': '호출 한도 초과'}, status=429)

    # 저장된 Q&A 우선 매칭 (토큰 절약) — 빠른메뉴와 거의 동일한 질문만 DB 답변 반환
    cached = _match_cached_qna(project, question)
    if cached:
        # AI가 생각하는 듯한 자연스러운 UX를 위해 짧은 지연 후 반환
        time.sleep(2)
        cleaned = strip_instruction_echo(cached.answer_md) or cached.answer_md
        record(project.user, project, 'chat')
        _log(request, 'ok', 'cached_qna', public_id)
        return _gemini_shape(cleaned)

    prompt = f"{widget.system_prompt}\n\n{memory}\n사용자 질문: {question}"
    try:
        # 실시간 채팅: 응답 토큰 상한과 짧은 타임아웃으로 지연 최소화
        # 테넌트(project)별 Gemini 키/모델 설정을 우선 적용한다.
        answer = ask(prompt, max_tokens=1024, timeout=30.0, project=project)
    except Exception as e:  # noqa: BLE001
        _log(request, 'blocked_401', f'llm_error:{str(e)[:120]}', public_id)
        return JsonResponse({'error': 'AI 호출 실패'}, status=502)
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
        return JsonResponse({'error': '잘못된 요청'}, status=400)

    public_id = (body.get('publicId') or '').strip()
    question = (body.get('question') or '').strip()
    error_message = (body.get('errorMessage') or '').strip()
    error_detail = (body.get('errorDetail') or '').strip()

    if not error_message:
        return JsonResponse({'error': 'errorMessage 필요'}, status=400)

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
