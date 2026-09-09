"""위젯 채팅 API CORS 미들웨어.

위젯은 고객 사이트(다른 오리진)에 임베드되어 WebMCP 서버로 크로스오리진 요청을
보낸다. 브라우저가 이를 허용하려면 서버가 CORS 헤더를 반환해야 한다.

- Origin 화이트리스트(TenantOrigin)에 등록된 오리진에만 CORS 허용.
- OPTIONS preflight 요청은 200 + CORS 헤더로 응답 (본 요청은 뷰가 처리).
- credentials(세션 쿠키)를 쓰므로 `Access-Control-Allow-Origin: *` 는 불가 —
  요청 Origin 을 그대로 echo 하고 `Access-Control-Allow-Credentials: true` 를 붙인다.
"""
from __future__ import annotations

from django.http import HttpResponse

from core.origins import normalize_origin

# CORS 를 적용할 경로 접두사 (위젯이 호출하는 데이터 플레인 API)
CORS_PATHS = ('/api/chat/', '/api/chat/page-answer/', '/api/chat/report/', '/api/health/', '/health/')


def _origin_allowed(origin: str) -> bool:
    """Origin 이 어떤 프로젝트의 화이트리스트에 등록되어 있는지 확인."""
    if not origin:
        return False
    try:
        normalized = normalize_origin(origin)
    except Exception:  # noqa: BLE001 — 잘못된 Origin 은 허용하지 않음
        return False
    from apps.projects.models import TenantOrigin
    return TenantOrigin.objects.filter(origin=normalized, enabled=True).exists()


class WidgetCorsMiddleware:
    """위젯 채팅 API에만 CORS 헤더를 적용하는 경량 미들웨어."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get('origin') or ''
        path = request.path

        # 위젯 채팅 API 경로에만 적용
        is_widget_api = any(path.startswith(p) for p in CORS_PATHS)

        if is_widget_api and origin and _origin_allowed(origin):
            # OPTIONS preflight — 본 요청 없이 CORS 헤더만 반환
            if request.method == 'OPTIONS':
                resp = HttpResponse(status=200)
                resp['Access-Control-Allow-Origin'] = origin
                resp['Access-Control-Allow-Credentials'] = 'true'
                resp['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
                resp['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
                resp['Access-Control-Max-Age'] = '86400'
                return resp

            # 본 요청 — 응답에 CORS 헤더 부착
            response = self.get_response(request)
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Credentials'] = 'true'
            return response

        return self.get_response(request)
