import logging
import time

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from core.langsilo import msg

from .models import User
from .serializers import MeSerializer, PasswordChangeSerializer, ProfileSerializer, SignupSerializer

logger = logging.getLogger(__name__)

# ── 무작위 로그인(브루트포스) 방어 ─────────────────────────────
# 인메모리 실패 카운터: {key: (실패 횟수, 첫 실패 시각)}
# key = "ip|email" 조합. 동일 키로 연속 실패 시 로그인을 잠근다.
_FAILED_ATTEMPTS: dict[str, list] = {}
MAX_ATTEMPTS = 5          # 허용 실패 횟수
LOCK_WINDOW = 300         # 실패 집계 창 (초, 5분)
LOCK_DURATION = 300       # 잠금 지속 시간 (초, 5분)


def _client_ip(request) -> tuple:
    """(클라이언트 IP, 직접 연결 여부) 반환.

    - X-Forwarded-For 헤더가 있으면(프록시 경유) 첫 번째 IP 사용, direct=False
    - 없으면(직접 연결) REMOTE_ADDR 사용, direct=True
      → 이 경우 사설망/루프백이면 ipguard 에서 항상 허용(락아웃 방지)
    - 'IP:포트'·'[IPv6]:포트' 형태(IIS ARR 등)는 core.clientip 에서 정제
    """
    from core.clientip import client_ip
    fwd = request.META.get('HTTP_X_FORWARDED_FOR')
    direct = not fwd
    return client_ip(request), direct


def _is_locked(key: str):
    """잠금 상태 판단. (잠김 여부, 남은 초) 반환."""
    entry = _FAILED_ATTEMPTS.get(key)
    if not entry:
        return False, 0
    count, first_ts = entry
    now = time.time()
    # 잠금 중: 카운트가 MAX를 넘었고 잠금 시간이 지나지 않았으면 차단
    if count >= MAX_ATTEMPTS and (now - first_ts) < (LOCK_WINDOW + LOCK_DURATION):
        return True, int((LOCK_WINDOW + LOCK_DURATION) - (now - first_ts))
    # 집계 창이 지났으면 초기화
    if (now - first_ts) > (LOCK_WINDOW + LOCK_DURATION):
        _FAILED_ATTEMPTS.pop(key, None)
        return False, 0
    return False, 0


def _record_failure(key: str):
    entry = _FAILED_ATTEMPTS.get(key)
    now = time.time()
    if entry and (now - entry[1]) < LOCK_WINDOW:
        _FAILED_ATTEMPTS[key] = (entry[0] + 1, entry[1])
    else:
        _FAILED_ATTEMPTS[key] = (1, now)


def _clear_failures(key: str):
    _FAILED_ATTEMPTS.pop(key, None)


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
    ip, direct = _client_ip(request)
    key = f'{ip}|{email.strip().lower()}'

    # 무작위 로그인 방어: 실패 횟수 초과 시 잠금
    locked, remaining = _is_locked(key)
    if locked:
        logger.warning('LOGIN BLOCKED email=%s ip=%s remaining=%ss', email, ip, remaining)
        return Response(
            {'detail': msg('auth.tooManyAttempts', seconds=remaining)},
            status=429,
        )

    user = authenticate(request, username=email, password=password)
    if user is None:
        _record_failure(key)
        entry = _FAILED_ATTEMPTS.get(key)
        count = entry[0] if entry else 1
        logger.warning('LOGIN FAIL email=%s ip=%s reason=invalid_credentials count=%s', email, ip, count)
        return Response({'detail': msg('auth.invalidCredentials')}, status=401)
    if not user.is_active:
        _record_failure(key)
        logger.warning('LOGIN FAIL email=%s ip=%s reason=inactive', email, ip)
        return Response({'detail': msg('auth.invalidCredentials')}, status=401)

    # IP 화이트리스트 확인 — 등록된 IP만 로그인 허용 (비어 있으면 제한 없음)
    # direct(프록시 없는 직접 연결)이고 사설망/루프백이면 항상 허용(락아웃 방지)
    from .ipguard import ip_allowed
    if not ip_allowed(getattr(user, 'allowed_ips', ''), ip, direct=direct):
        _record_failure(key)
        logger.warning('LOGIN DENIED email=%s ip=%s reason=ip_not_allowed', email, ip)
        return Response({'detail': msg('auth.ipNotAllowed')}, status=403)

    login(request, user)          # 세션 로테이션 포함
    _clear_failures(key)          # 성공 시 실패 카운터 초기화
    logger.info('LOGIN OK email=%s id=%s ip=%s', email, user.id, ip)
    return Response(MeSerializer(user).data)


@csrf_exempt
def logout_view(request):
    """로그아웃 — DRF SessionAuthentication 의 CSRF 강제를 우회하기 위해
    순수 Django 뷰로 처리한다. 로그아웃은 무해한 동작이므로 CSRF/인증 없이
    항상 세션을 삭제해 비정상 접속을 차단한다."""
    if request.method == 'POST':
        logout(request)
        return JsonResponse({'ok': True})
    return JsonResponse({'detail': msg('auth.postOnly')}, status=405)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    # IP 화이트리스트 — 세션 중 다른 IP 접속 탐지 시 즉시 세션 무효화
    from .ipguard import ip_allowed
    ip, direct = _client_ip(request)
    if not ip_allowed(getattr(request.user, 'allowed_ips', ''), ip, direct=direct):
        logout(request)
        logger.warning('ME DENIED email=%s ip=%s reason=ip_not_allowed (session terminated)', request.user.email, ip)
        return Response({'detail': msg('auth.ipNotAllowed')}, status=403)
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


# ── 프로필 페이지 ────────────────────────────────────────────
DEFAULT_MONTHLY_PRICE = {'ko': ('KRW', 50000), 'en': ('USD', 49)}


def _default_price_for_silo() -> tuple[str, int]:
    """현재 사일로의 기본 월 결제 금액. ko=50,000원, en=$49."""
    from django.conf import settings as dj_settings
    lang = getattr(dj_settings, 'WEBMCP_LANG', 'ko')
    return DEFAULT_MONTHLY_PRICE.get(lang, DEFAULT_MONTHLY_PRICE['ko'])


def _profile_payload(user: User) -> dict:
    """프로필 응답 — 본인 정보 + 결제 안내(기본가/엔터프라이즈 여부)."""
    data = ProfileSerializer(user).data
    currency, price = _default_price_for_silo()
    # admin이 금액을 지정했으면 엔터프라이즈로 표시
    overridden = user.monthly_price is not None
    data['billing'] = {
        'defaultCurrency': currency,
        'defaultPrice': float(price),
        'amount': float(user.monthly_price) if overridden else float(price),
        'currency': user.monthly_currency or currency,
        'isEnterprise': overridden,
        # 결제 수단 연동 전 테스트용 플레이스홀더
        'paymentReady': False,
    }
    # 사이트 대표 연락처 (오류 안내 문구에 노출되는 번호 — admin만 수정)
    from apps.proxy.models import SiteSetting
    from django.conf import settings as dj_settings
    data['supportPhone'] = SiteSetting.get('support_phone', dj_settings.SUPPORT_PHONE)
    return data


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def profile(request):
    """내 프로필 조회/수정 (일반/관리자 공용)."""
    user = request.user
    if request.method == 'GET':
        return Response(_profile_payload(user))

    s = ProfileSerializer(user, data=request.data, partial=True)
    s.is_valid(raise_exception=True)
    s.save()
    return Response(_profile_payload(user))
