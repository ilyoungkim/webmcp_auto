from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.catalogs.models import DomainType
from apps.pipeline.crawler import fetch_sitemap_items, fetch_sitemap_urls
from core.langsilo import msg
from core.origins import normalize_origin

from .models import Project, TenantOrigin
from .serializers import OriginSerializer, ProjectDetailSerializer, ProjectListSerializer


def _get_owned(request, pk) -> Project:
    project = Project.objects.filter(pk=pk).first()
    if project is None:
        raise ValidationError(msg('project.notFound'))
    if project.user_id != request.user.id and request.user.role != 'admin':
        raise PermissionDenied()
    return project


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def projects(request):
    if request.method == 'GET':
        qs = Project.objects.filter(user=request.user)
        return Response(ProjectListSerializer(qs, many=True, context={'public_url': settings.SAAS_PUBLIC_URL}).data)

    # POST — 플랜 한도 검사 (최대 5개 제한)
    plan = settings.PLANS.get(request.user.plan, settings.PLANS['free'])
    max_projects = plan.get('max_projects', 5)
    if max_projects is not None and Project.objects.filter(user=request.user).count() >= max_projects:
        return Response({'detail': msg('project.limitReached', max=max_projects)}, status=400)

    name = (request.data.get('name') or '').strip()
    url = (request.data.get('url') or '').strip()
    code = (request.data.get('domainTypeCode') or '').strip()
    if not name or not url or not code:
        raise ValidationError(msg('project.fieldsRequired'))
    # 언어 사일로 — 컨테이너의 언어에 맞는 카탈로그만 노출되므로 code 탐색도 현재 언어로 제한
    from core.langsilo import current_lang
    cur_lang = current_lang()
    dt = DomainType.objects.filter(code=code, enabled=True, lang__in=[cur_lang, '']).first()
    if dt is None:
        raise ValidationError(msg('project.unknownDomainType'))

    project = Project.objects.create(
        user=request.user, name=name, url=url,
        origin=normalize_origin(url), domain_type=dt,
        theme=(request.data.get('theme') or 'blue_sky'),
        lang=dt.lang or cur_lang,  # 프로젝트 언어 = 카탈로그(도메인 유형)의 언어
    )
    TenantOrigin.objects.get_or_create(origin=project.origin, defaults={'project': project})
    from apps.pipeline.models import PipelineJob
    # 생성 시 선택한 소스 페이지(최대 10개)가 있으면 해당 URL로 크롤링
    selected_urls = request.data.get('selectedUrls') or []
    if not isinstance(selected_urls, list):
        selected_urls = []
    selected_urls = [u.strip() for u in selected_urls if isinstance(u, str) and u.strip()][:10]
    PipelineJob.objects.create(project=project, selected_urls=selected_urls)
    return Response(ProjectDetailSerializer(project, context={'public_url': settings.SAAS_PUBLIC_URL}).data, status=201)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def project_detail(request, pk):
    p = _get_owned(request, pk)
    if request.method == 'DELETE':
        p.delete()
        return Response({'ok': True})
    if request.method in ('PUT', 'PATCH'):
        data = request.data
        # 이름/URL은 변경 불가 — 도메인 유형과 테마만 변경 가능
        code = (data.get('domainTypeCode') or '').strip()
        if code:
            dt = DomainType.objects.filter(code=code, enabled=True).first()
            if dt is None:
                raise ValidationError(msg('project.unknownDomainType'))
            p.domain_type = dt
        theme = (data.get('theme') or '').strip()
        if theme:
            from core.themes import THEME_CODES
            if theme not in THEME_CODES:
                raise ValidationError(msg('project.unknownTheme'))
            p.theme = theme
        p.save()
        # 테마/정보 변경 시 위젯 재빌드 (기존 소스 기반)
        if theme:
            from apps.pipeline.models import GeneratedQnA, SiteContent
            from apps.pipeline.runner import regenerate_qna
            from apps.widgets.generator import build_widget
            from apps.catalogs.models import QuickMenu
            content = SiteContent.objects.filter(project=p).first()
            if content and content.markdown:
                menus = list(QuickMenu.objects.filter(domain_type=p.domain_type, enabled=True))
                qna_rows = list(GeneratedQnA.objects.filter(project=p))
                build_widget(p, menus, content.markdown, qna_rows=qna_rows)
        return Response(ProjectDetailSerializer(p, context={'public_url': settings.SAAS_PUBLIC_URL}).data)
    return Response(ProjectDetailSerializer(p, context={'public_url': settings.SAAS_PUBLIC_URL}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_status(request, pk):
    p = _get_owned(request, pk)
    return Response({'status': p.status, 'progress': p.progress, 'statusMessage': p.status_message})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_sitemap_urls(request, pk):
    """프로젝트 URL 기준으로 sitemap에서 root에 가까운 낮은 depth 순 상위 30개 URL 목록을 조회."""
    p = _get_owned(request, pk)
    # 쿼리 파라미터로 url이 넘어온 경우 해당 url 기준(수정 폼에서 입력한 새 URL 등)으로 조회 가능
    target_url = (request.query_params.get('url') or p.url).strip()
    items = fetch_sitemap_items(target_url, limit=30)
    urls = [item['url'] for item in items]
    return Response({'urls': urls, 'items': items})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sitemap_urls(request):
    """새 프로젝트 생성 전, 입력 URL 기준으로 상위 30개 URL 목록을 조회."""
    target_url = (request.query_params.get('url') or '').strip()
    if not target_url:
        raise ValidationError(msg('project.urlRequired'))
    items = fetch_sitemap_items(target_url, limit=30)
    urls = [item['url'] for item in items]
    return Response({'urls': urls, 'items': items})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def project_rerun(request, pk):
    p = _get_owned(request, pk)
    selected_urls = request.data.get('selectedUrls') or []
    if not isinstance(selected_urls, list):
        selected_urls = []
    # 최대 10개로 제한
    selected_urls = [u.strip() for u in selected_urls if isinstance(u, str) and u.strip()][:10]

    from apps.pipeline.models import PipelineJob
    PipelineJob.objects.create(project=p, selected_urls=selected_urls)
    p.status = 'queued'
    p.status_message = ''
    p.error = ''
    p.save(update_fields=['status', 'status_message', 'error', 'updated_at'])
    return Response({'ok': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_menus(request, pk):
    """빠른메뉴 목록과 현재 질문/답변을 조회 (편집용)."""
    p = _get_owned(request, pk)
    from apps.catalogs.models import QuickMenu
    from apps.pipeline.models import GeneratedQnA

    menus = QuickMenu.objects.filter(domain_type=p.domain_type, enabled=True, is_required=False)
    qna_map = {q.menu_label: q for q in GeneratedQnA.objects.filter(project=p)}
    return Response({
        'edited': p.menus_edited,
        'menus': [
            {
                'label': m.label,
                'question': qna_map[m.label].question if m.label in qna_map else m.question,
                'answerMd': qna_map[m.label].answer_md if m.label in qna_map else '',
            }
            for m in menus
        ]
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def project_menus_regenerate(request, pk):
    """편집된 빠른메뉴 질문으로, 이미 수집된 소스(markdown) 기반 답변을 재생성한다.

    - 재크롤링 없이 저장된 SiteContent.markdown만 사용.
    - 질문이 비어 있으면 기존/자동 생성 질문을 사용.
    - 생성된 Q&A와 위젯 config를 함께 갱신.
    """
    p = _get_owned(request, pk)
    from apps.catalogs.models import QuickMenu
    from apps.pipeline.models import GeneratedQnA, SiteContent
    from apps.pipeline.runner import regenerate_qna
    from apps.widgets.generator import build_widget

    # 빠른메뉴 질문 편집은 1회만 허용
    if p.menus_edited:
        raise ValidationError(msg('project.menuEditOnce'))

    content = SiteContent.objects.filter(project=p).first()
    if content is None or not content.markdown:
        raise ValidationError(msg('project.noSources'))

    menus = list(QuickMenu.objects.filter(domain_type=p.domain_type, enabled=True, is_required=False))
    if not menus:
        raise ValidationError(msg('project.noMenus'))

    # 사용자가 편집한 질문 매핑 (menu_label → question) — 필수 메뉴는 제외
    questions_map: dict[str, str] = {}
    for d in (request.data.get('menus') or []):
        if isinstance(d, dict) and d.get('label'):
            questions_map[d['label']] = (d.get('question') or '').strip()

    qna_rows = regenerate_qna(p, content.markdown, menus, questions_map)
    GeneratedQnA.objects.filter(project=p).delete()
    GeneratedQnA.objects.bulk_create(qna_rows)
    build_widget(p, menus, content.markdown, qna_rows=qna_rows)
    # 편집 1회 사용 완료 처리
    p.menus_edited = True
    p.save(update_fields=['menus_edited', 'updated_at'])
    return Response({'ok': True, 'menus': [
        {'label': r.menu_label, 'question': r.question, 'answerMd': r.answer_md}
        for r in qna_rows
    ]})


@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def project_origins(request, pk, origin_id=None):
    p = _get_owned(request, pk)
    if request.method == 'POST':
        origin = normalize_origin((request.data.get('origin') or '').strip())
        obj, created = TenantOrigin.objects.get_or_create(origin=origin, defaults={'project': p})
        if not created and obj.project_id != p.id:
            raise ValidationError(msg('project.originTaken'))
        return Response(OriginSerializer(obj).data, status=201)
    obj = TenantOrigin.objects.filter(pk=origin_id, project=p).first()
    if obj is None:
        raise ValidationError(msg('project.originNotFound'))
    if TenantOrigin.objects.filter(project=p).count() <= 1:
        raise ValidationError(msg('project.originMinimum'))
    obj.delete()
    return Response({'ok': True})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def project_support(request, pk):
    """고객센터 Q&A 게시판 — 사용자가 질문을 올리고 답변을 확인한다.

    GET: 페이지네이션(10개/페이지)으로 질문 목록 조회
    POST: 새 질문 등록
    """
    p = _get_owned(request, pk)
    from .models import SupportTicket

    if request.method == 'POST':
        question = (request.data.get('question') or '').strip()
        if not question:
            raise ValidationError(msg('project.questionRequired'))
        if len(question) > 2000:
            raise ValidationError(msg('project.questionTooLong'))
        ticket = SupportTicket.objects.create(
            project=p, user=request.user, question=question,
        )
        return Response(_support_ticket_data(ticket), status=201)

    # GET — 페이지네이션 (10개/페이지)
    page = max(int(request.query_params.get('page') or 1), 1)
    per_page = 10
    qs = SupportTicket.objects.filter(project=p)
    total = qs.count()
    total_pages = max((total + per_page - 1) // per_page, 1)
    page = min(page, total_pages)
    items = qs[(page - 1) * per_page: page * per_page]
    return Response({
        'items': [_support_ticket_data(t) for t in items],
        'page': page,
        'totalPages': total_pages,
        'total': total,
    })


def _support_ticket_data(t) -> dict:
    return {
        'id': t.id,
        'projectId': t.project_id,
        'projectName': t.project.name,
        'question': t.question,
        'answer': t.answer,
        'status': t.status,
        'createdAt': t.created_at.isoformat(),
        'answeredAt': t.answered_at.isoformat() if t.answered_at else '',
    }
