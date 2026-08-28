from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import DomainType
from .serializers import DomainTypeSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def domain_types(request):
    qs = DomainType.objects.filter(enabled=True).prefetch_related('menus')
    return Response(DomainTypeSerializer(qs, many=True).data)
