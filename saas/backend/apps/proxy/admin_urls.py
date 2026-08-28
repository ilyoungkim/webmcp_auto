"""관리자 API (role=admin 전용)."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

User = get_user_model()


def _require_admin(request):
    if request.user.role != 'admin':
        raise PermissionDenied()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def users(request):
    _require_admin(request)
    return Response([
        {'id': u.id, 'email': u.email, 'name': u.name, 'role': u.role,
         'plan': u.plan, 'active': u.is_active}
        for u in User.objects.order_by('id')
    ])


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def user_patch(request, pk):
    _require_admin(request)
    u = User.objects.filter(pk=pk).first()
    if u is None:
        raise ValidationError('사용자 없음')
    for field in ('role', 'plan'):
        if field in request.data:
            setattr(u, field, request.data[field])
    if 'active' in request.data:
        u.is_active = bool(request.data['active'])
    u.save()
    return Response({'ok': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def usage(request):
    _require_admin(request)
    from django.db.models import Count

    from .models import UsageEvent
    counts = {r['kind']: r['n'] for r in UsageEvent.objects.values('kind').annotate(n=Count('id'))}
    return Response({'usage': counts})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chat_errors(request):
    """챗 오류 신고 목록 (관리자 전용)."""
    _require_admin(request)
    from .models import ChatErrorReport

    status = (request.query_params.get('status') or '').strip()
    qs = ChatErrorReport.objects.all()
    if status:
        qs = qs.filter(status=status)
    return Response([
        {
            'id': r.id,
            'publicId': r.public_id,
            'projectName': r.project.name if r.project else '',
            'origin': r.origin,
            'question': r.question,
            'errorMessage': r.error_message,
            'errorDetail': r.error_detail,
            'ip': str(r.ip) if r.ip else '',
            'userAgent': r.user_agent,
            'status': r.status,
            'createdAt': r.created_at.isoformat(),
        }
        for r in qs[:200]
    ])


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def chat_error_patch(request, pk):
    """챗 오류 신고 상태 변경 (관리자 전용)."""
    _require_admin(request)
    from .models import ChatErrorReport

    r = ChatErrorReport.objects.filter(pk=pk).first()
    if r is None:
        raise ValidationError('신고 없음')
    status = (request.data.get('status') or '').strip()
    if status and status in dict(ChatErrorReport.STATUS):
        r.status = status
        r.save(update_fields=['status', 'updated_at'])
    return Response({'ok': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_projects(request):
    """전체 프로젝트 목록 (관리자 전용, Q&A 재생성용).

    ?user_id=<id> 로 특정 사용자의 프로젝트만 조회할 수 있다.
    """
    _require_admin(request)
    from apps.projects.models import Project

    qs = Project.objects.select_related('domain_type', 'user').order_by('-created_at')
    user_id = (request.query_params.get('user_id') or '').strip()
    if user_id:
        qs = qs.filter(user_id=user_id)
    return Response([
        {
            'id': p.id,
            'name': p.name,
            'url': p.url,
            'publicId': p.public_id,
            'userId': p.user_id,
            'userEmail': p.user.email if p.user else '',
            'domainTypeCode': p.domain_type.code if p.domain_type else '',
            'domainTypeName': p.domain_type.name if p.domain_type else '',
            'status': p.status,
            'enabled': p.enabled,
        }
        for p in qs[:500]
    ])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_project_regenerate(request, pk):
    """프로젝트 Q&A 재생성 (관리자 전용).

    재크롤링 없이 저장된 SiteContent.markdown으로 빠른메뉴 질문/답변을
    배치 생성(단일 API 호출)하고 위젯 config를 갱신한다.
    """
    _require_admin(request)
    from apps.catalogs.models import QuickMenu
    from apps.pipeline.models import GeneratedQnA, SiteContent
    from apps.pipeline.runner import regenerate_qna
    from apps.projects.models import Project
    from apps.widgets.generator import build_widget

    p = Project.objects.filter(pk=pk).first()
    if p is None:
        raise ValidationError('프로젝트 없음')

    content = SiteContent.objects.filter(project=p).first()
    if content is None or not content.markdown:
        raise ValidationError('수집된 소스가 없습니다. 먼저 크롤링을 실행하세요.')

    menus = list(QuickMenu.objects.filter(domain_type=p.domain_type, enabled=True))
    if not menus:
        raise ValidationError('빠른메뉴가 설정되지 않았습니다.')

    qna_rows = regenerate_qna(p, content.markdown, menus)
    GeneratedQnA.objects.filter(project=p).delete()
    GeneratedQnA.objects.bulk_create(qna_rows)
    build_widget(p, menus, content.markdown, qna_rows=qna_rows)
    return Response({'ok': True, 'count': len(qna_rows), 'menus': [
        {'label': r.menu_label, 'question': r.question, 'answerMd': r.answer_md}
        for r in qna_rows
    ]})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_project_toggle(request, pk):
    """프로젝트 사용중지/사용재개 토글 (관리자 전용)."""
    _require_admin(request)
    from apps.projects.models import Project

    p = Project.objects.filter(pk=pk).first()
    if p is None:
        raise ValidationError('프로젝트 없음')
    p.enabled = not p.enabled
    p.save(update_fields=['enabled', 'updated_at'])
    return Response({'ok': True, 'enabled': p.enabled})


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def admin_project_llm(request, pk):
    """프로젝트(테넌트)별 LLM 설정 조회/수정 (관리자 전용).

    GET: 현재 프로젝트에 저장된 테넌트 설정과 전역 기본값을 함께 반환.
    PATCH: 프로젝트별 Gemini API 키/모델을 저장. 빈 문자열로 보내면 해당
    항목을 초기화해 전역 settings(.env) 값을 사용하도록 되돌린다.
    (OpenRouter는 전역 .env 로만 관리한다.)
    """
    _require_admin(request)
    from apps.projects.models import Project

    p = Project.objects.filter(pk=pk).first()
    if p is None:
        raise ValidationError('프로젝트 없음')

    if request.method == 'GET':
        return Response({
            'projectId': p.id,
            'projectName': p.name,
            # 테넌트에 저장된 값 (빈 문자열 = 전역 사용)
            'geminiApiKey': p.gemini_api_key,
            'geminiModel': p.gemini_model,
            # 전역 기본값 (참고용)
            'defaults': {
                'geminiModel': settings.GEMINI_MODEL,
            },
        })

    # PATCH — 저장/초기화 (Gemini 전용)
    fields = {
        'geminiApiKey': 'gemini_api_key',
        'geminiModel': 'gemini_model',
    }
    changed = []
    for api_field, model_field in fields.items():
        if api_field in request.data:
            val = (request.data[api_field] or '').strip()
            setattr(p, model_field, val)
            changed.append(api_field)
    if changed:
        p.save(update_fields=list(fields.values()) + ['updated_at'])
    return Response({'ok': True, 'changed': changed})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_project_llm_test(request, pk):
    """프로젝트(테넌트)별 Gemini API 키 테스트 + 적용 (관리자 전용).

    요청 본문에 geminiApiKey/geminiModel 을 받는다.
    - 키가 주어지면 그 키로 실제 호출해 검증한다.
    - 키가 비어 있으면 프로젝트에 저장된 키(없으면 전역 .env 키)로 테스트.
    - 테스트가 성공하면 해당 키/모델을 프로젝트에 저장(적용)한다.
    - 테스트가 실패하면 저장하지 않고 오류 메시지를 반환한다.
    """
    _require_admin(request)
    from apps.projects.models import Project
    from core.llm import GeminiError, test_gemini_key

    p = Project.objects.filter(pk=pk).first()
    if p is None:
        raise ValidationError('프로젝트 없음')

    # 테스트할 키/모델 결정: 요청값 > 프로젝트 저장값 > 전역
    api_key = (request.data.get('geminiApiKey') or '').strip()
    model = (request.data.get('geminiModel') or '').strip()
    if not api_key:
        api_key = p.gemini_api_key
    if not model:
        model = p.gemini_model

    try:
        reply = test_gemini_key(api_key, model)
    except GeminiError as e:
        return Response({'ok': False, 'error': str(e)}, status=400)

    # 테스트 성공 → 프로젝트에 적용(저장). 빈 값이면 전역 사용으로 초기화.
    p.gemini_api_key = api_key
    p.gemini_model = model
    p.save(update_fields=['gemini_api_key', 'gemini_model', 'updated_at'])

    return Response({
        'ok': True,
        'reply': reply,
        'model': model or settings.GEMINI_MODEL,
        'applied': True,
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def admin_project_delete(request, pk):
    """프로젝트 삭제 (관리자 전용)."""
    _require_admin(request)
    from apps.projects.models import Project

    p = Project.objects.filter(pk=pk).first()
    if p is None:
        raise ValidationError('프로젝트 없음')
    name = p.name
    p.delete()
    return Response({'ok': True, 'name': name})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_support(request):
    """고객센터 Q&A 목록 (관리자 전용).

    ?user_id=<id> 로 특정 사용자가 올린 질문만 조회할 수 있다.
    페이지네이션 10개/페이지.
    """
    _require_admin(request)
    from apps.projects.models import SupportTicket

    qs = SupportTicket.objects.select_related('project', 'user').order_by('-created_at')
    user_id = (request.query_params.get('user_id') or '').strip()
    if user_id:
        qs = qs.filter(user_id=user_id)

    page = max(int(request.query_params.get('page') or 1), 1)
    per_page = 10
    total = qs.count()
    total_pages = max((total + per_page - 1) // per_page, 1)
    page = min(page, total_pages)
    items = qs[(page - 1) * per_page: page * per_page]
    return Response({
        'items': [
            {
                'id': t.id,
                'projectId': t.project_id,
                'projectName': t.project.name,
                'userId': t.user_id,
                'userEmail': t.user.email if t.user else '',
                'question': t.question,
                'answer': t.answer,
                'status': t.status,
                'createdAt': t.created_at.isoformat(),
                'answeredAt': t.answered_at.isoformat() if t.answered_at else '',
            }
            for t in items
        ],
        'page': page,
        'totalPages': total_pages,
        'total': total,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_support_answer(request, pk):
    """고객센터 Q&A 답변 등록 (관리자 전용)."""
    _require_admin(request)
    from django.utils import timezone

    from apps.projects.models import SupportTicket

    t = SupportTicket.objects.filter(pk=pk).first()
    if t is None:
        raise ValidationError('Q&A 없음')
    answer = (request.data.get('answer') or '').strip()
    if not answer:
        raise ValidationError('답변 내용을 입력해주세요.')
    t.answer = answer
    t.status = 'answered'
    t.answered_at = timezone.now()
    t.save(update_fields=['answer', 'status', 'answered_at'])
    return Response({'ok': True, 'id': t.id, 'status': t.status, 'answer': t.answer})


urlpatterns = [
    path('users/', users),
    path('users/<int:pk>/plan/', user_patch),
    path('users/<int:pk>/', user_patch),
    path('usage/', usage),
    path('chat-errors/', chat_errors),
    path('chat-errors/<int:pk>/', chat_error_patch),
    path('projects/', admin_projects),
    path('projects/<int:pk>/regenerate/', admin_project_regenerate),
    path('projects/<int:pk>/toggle/', admin_project_toggle),
    path('projects/<int:pk>/llm/', admin_project_llm),
    path('projects/<int:pk>/llm/test/', admin_project_llm_test),
    path('projects/<int:pk>/', admin_project_delete),
    path('support/', admin_support),
    path('support/<int:pk>/answer/', admin_support_answer),
]
