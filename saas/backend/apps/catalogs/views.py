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
