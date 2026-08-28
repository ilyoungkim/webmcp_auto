import logging

from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import User
from .serializers import MeSerializer, PasswordChangeSerializer, SignupSerializer

logger = logging.getLogger(__name__)


@ensure_csrf_cookie
@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    s = SignupSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    data = s.validated_data
    user = User.objects.create_user(
        email=data['email'], password=data['password'], name=data.get('name', '')
    )
    login(request, user)
    logger.info('SIGNUP OK email=%s id=%s', data['email'], user.id)
    return Response(MeSerializer(user).data, status=201)


@ensure_csrf_cookie
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    email = request.data.get('email', '')
    password = request.data.get('password', '')
    user = authenticate(request, username=email, password=password)
    if user is None:
        logger.warning('LOGIN FAIL email=%s reason=invalid_credentials', email)
        return Response({'detail': '자격 증명이 올바르지 않습니다.'}, status=401)
    if not user.is_active:
        logger.warning('LOGIN FAIL email=%s reason=inactive', email)
        return Response({'detail': '자격 증명이 올바르지 않습니다.'}, status=401)
    login(request, user)          # 세션 로테이션 포함
    logger.info('LOGIN OK email=%s id=%s', email, user.id)
    return Response(MeSerializer(user).data)


@api_view(['POST'])
def logout_view(request):
    logout(request)
    return Response({'ok': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(MeSerializer(request.user).data)


@ensure_csrf_cookie
@api_view(['GET'])
@permission_classes([AllowAny])
def csrf_token(request):
    """SPA 마운트 시 호출해 csrftoken 쿠키를 미리 발급한다.
    인증된 요청의 POST 는 DRF 가 CSRF 를 강제하므로,
    프론트엔드가 이 엔드포인트로 쿠키를 확보해 두면 로그인/생성 요청이 403 되지 않는다."""
    return Response({'ok': True})


@api_view(['POST'])
def change_password(request):
    s = PasswordChangeSerializer(data=request.data, context={'request': request})
    s.is_valid(raise_exception=True)
    user = request.user
    user.set_password(s.validated_data['new'])
    user.must_change_password = False
    user.save(update_fields=['password', 'must_change_password'])
    from django.contrib.auth import update_session_auth_hash

    update_session_auth_hash(request, user)
    return Response({'ok': True})
