"""위젯 채팅 API CORS 미들웨어.

위젯은 고객 사이트(다른 오리진)에 임베드되어 WebMCP 서버로 크로스오리진 요청을
보낸다. 브라우저가 이를 허용하려면 서버가 CORS 헤더를 반환해야 한다.

- CORS 헤더는 위젯 API 경로에 대해 **항상** 요청 Origin 을 echo 한다.
  실제 보안 검증(Origin 화이트리스트 + 자동학습 + 403)은 뷰(proxy/views.py)가
  담당한다. CORS 헤더는 "브라우저가 응답을 읽을 수 있게" 할 뿐 데이터 보호는
  뷰의 403 이 담당하므로, 화이트리스트에 없는 오리진에도 헤더를 echo 해도 안전하다.
- credentials(세션 쿠키)를 쓰므로 `Access-Control-Allow-Origin: *` 는 불가 —
  요청 Origin 을 그대로 echo 하고 `Access-Control-Allow-Credentials: true` 를 붙인다.
- OPTIONS preflight 는 본 요청 없이 CORS 헤더만 반환한다.
"""
from __future__ import annotations

from django.http import HttpResponse

# CORS 를 적용할 경로 접두사 (위젯이 호출하는 데이터 플레인 API)
CORS_PATHS = ('/api/chat/', '/api/chat/page-answer/', '/api/chat/report/', '/api/health/', '/health/')


class WidgetCorsMiddleware:
    """위젯 채팅 API에 CORS 헤더를 적용하는 경량 미들웨어.

    화이트리스트 검증은 하지 않는다 — 뷰가 담당한다. (미들웨어가 먼저 검사하면
    뷰의 "origin 자동 학습"이 동작하기 전에 차단되어 닭-달걀 문제가 생긴다.)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get('origin') or ''
        path = request.path

        # 위젯 채팅 API 경로에만 적용
        is_widget_api = any(path.startswith(p) for p in CORS_PATHS)

        if is_widget_api and origin:
            # OPTIONS preflight — 본 요청 없이 CORS 헤더만 반환
            if request.method == 'OPTIONS':
                resp = HttpResponse(status=200)
                resp['Access-Control-Allow-Origin'] = origin
                resp['Access-Control-Allow-Credentials'] = 'true'
                resp['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
                resp['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
                resp['Access-Control-Max-Age'] = '86400'
                return resp

            # 본 요청 — 응답에 CORS 헤더 부착 (보안 검증은 뷰가 수행)
            response = self.get_response(request)
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Credentials'] = 'true'
            return response

        return self.get_response(request)
