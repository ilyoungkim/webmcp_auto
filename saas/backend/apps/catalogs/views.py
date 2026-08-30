from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.langsilo import current_lang

from .models import DomainType
from .serializers import DomainTypeSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def domain_types(request):
    """카탈로그 — 현재 사일로 언어에 속한 도메인 유형만 반환.

    언어별로 다른 카탈로그 소스를 사용해 사일로가 격리된다.
    예) WEBMCP_LANG=ko 인 컨테이너는 lang='ko' 카탈로그만 노출.
    """
    from core.langsilo import catalog_lang_tag
    tag = catalog_lang_tag()
    qs = DomainType.objects.filter(enabled=True, lang__in=[tag, '']) \
        if tag == 'ko' else DomainType.objects.filter(enabled=True, lang=tag)
    return Response(DomainTypeSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def silo_info(request):
    """현재 사일로 정보 — 콘솔 UI 다국어용.

    프론트엔드가 이 값을 읽어 콘솔 문구(업종 카테고리, 세부 유형, 빠른메뉴 등)를
    사일로 언어에 맞게 표시한다. 예) en 사일로 → {'lang': 'en', ...}
    """
    from core.langsilo import lang_meta, silo_summary
    summary = silo_summary()
    meta = lang_meta(summary['lang'])
    return Response({'lang': summary['lang'], 'label': meta.get('label', summary['lang'])})


@api_view(['GET'])
@permission_classes([AllowAny])
def site_info(request):
    """사이트 공개 정보 — 대표 연락처 등.

    로그인 없이 위젯 오류 안내 문구에 필요한 최소 정보만 반환한다.
    supportPhone: 관리자 프로필에서 수정 가능. 비어 있으면 settings 기본값.
    """
    from apps.proxy.models import SiteSetting
    from django.conf import settings as dj_settings
    return Response({
        'supportPhone': SiteSetting.get('support_phone', dj_settings.SUPPORT_PHONE),
    })
