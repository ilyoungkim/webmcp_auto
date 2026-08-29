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
