# ============================================================================
# webmcp/backend/app.py — FastAPI 기반 멀티테넌트 Gemini 프록시
# ============================================================================
# popup_agent_html.md 설계안 구현:
#   - DB(webmcp.tenants)에서 도메인별 Gemini 키/한도 조회 (gemini-key.js 미사용)
#   - Origin 헤더로 테넌트 판별 → 도메인별 키로 Gemini 호출
#   - 비정상 접속 감지(401) / 미등록 도메인(403) / Rate Limit(429)
#   - 모든 요청을 request_logs 에 로깅
# ============================================================================
import os
import json
import time
from collections import defaultdict

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pymysql
import pymysql.cursors
import httpx

load_dotenv()

# ── 설정 ──────────────────────────────────────────────────────
DB_HOST = os.getenv("DB_HOST", "192.168.31.136")
DB_USER = os.getenv("DB_USER", "fortune")
DB_PASSWORD = os.getenv("DB_PASSWORD", "user!1234@abcd")
DB_NAME = os.getenv("DB_NAME", "webmcp")

GEMINI_BASE = os.getenv("GEMINI_BASE", "https://generativelanguage.googleapis.com/v1beta")

# Client Hints 검증 (기본 비활성화 — 설계안 4-1-2)
REQUIRE_CLIENT_HINTS = os.getenv("REQUIRE_CLIENT_HINTS", "false").lower() == "true"

app = FastAPI(title="WebMCP Gemini Proxy")

# ── CORS ──────────────────────────────────────────────────────
# 허용 도메인은 DB(tenants)가 단일 진실 공급원입니다.
#   - 쿠키/인증정보를 사용하지 않으므로(allow_credentials=False) "*" 허용이 안전합니다.
#   - 실제 도메인 판별은 fetch_tenant()(DB 조회)가 담당 → 미등록 origin은 403 처리.
#   - 새 고객사 추가 시 코드 수정/재시작 없이 DB에 tenants 한 줄만 INSERT 하면 됩니다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# ── DB 커넥션 ─────────────────────────────────────────────────
def get_conn():
    return pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor, autocommit=True,
    )

def fetch_tenant(origin):
    """origin 에 해당하는 테넌트(도메인 설정)를 DB에서 조회합니다."""
    if not origin:
        return None
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM tenants WHERE origin=%s AND enabled=1 LIMIT 1",
                (origin,),
            )
            return cur.fetchone()
    finally:
        conn.close()

# ── Rate Limit (도메인 단위, 메모리) ──────────────────────────
_rate_counters = defaultdict(list)  # origin -> [timestamps]

def rate_limit_check(origin, max_per_minute):
    now = time.time()
    ts_list = _rate_counters[origin]
    ts_list[:] = [t for t in ts_list if t >= now - 60]
    if len(ts_list) >= max_per_minute:
        return False
    ts_list.append(now)
    return True

# ── 요청 로깅 ─────────────────────────────────────────────────
def log_request(req: Request, verdict: str, reason: str, body_len: int = 0):
    try:
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO request_logs
                       (origin, referer, user_agent, sec_ch_ua, ip, path, body_len, verdict, reason)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        req.headers.get("origin"),
                        req.headers.get("referer"),
                        req.headers.get("user-agent"),
                        req.headers.get("sec-ch-ua"),
                        (req.headers.get("x-forwarded-for") or (req.client.host if req.client else "unknown")).split(",")[0].strip(),
                        req.url.path,
                        body_len,
                        verdict,
                        reason,
                    ),
                )
        finally:
            conn.close()
    except Exception as e:
        print("[log_request] failed:", e)

# ── 비정상 접속 감지 (설계안 4-1-2) ───────────────────────────
def is_likely_real_browser(req: Request) -> bool:
    ua = req.headers.get("user-agent", "")
    chua = req.headers.get("sec-ch-ua", "")
    origin = req.headers.get("origin")
    referer = req.headers.get("referer", "")

    looks_like_browser = "Mozilla/5.0" in ua and any(x in ua for x in ("Chrome", "Firefox", "Safari", "Edg"))
    has_origin = bool(origin)  # 허용 여부는 DB(tenants)가 판별 → 여기선 존재 여부만 확인
    referer_ok = (not origin) or referer == "" or referer.startswith(origin)
    has_client_hints = (len(chua) > 0) if REQUIRE_CLIENT_HINTS else True

    return looks_like_browser and has_origin and referer_ok and has_client_hints

# ── Gemini 호출 ────────────────────────────────────────────────
async def call_gemini(tenant, prompt):
    url = f"{GEMINI_BASE}/models/{tenant['model_name']}:generateContent?key={tenant['gemini_key']}"
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            url,
            json={
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2, "topK": 3},
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API {resp.status_code}: {resp.text[:500]}")
        return resp.json()

# ── 헬스체크 ───────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "service": "webmcp-backend"}

# ── 채팅 프록시 ────────────────────────────────────────────────
@app.post("/api/chat")
async def chat(req: Request):
    origin = req.headers.get("origin")
    body = await req.body()
    body_len = len(body)

    if not is_likely_real_browser(req):
        log_request(req, "blocked_401", "header_missing_or_sparse", body_len)
        return JSONResponse({"error": "비정상적인 요청입니다."}, status_code=401)

    tenant = fetch_tenant(origin)
    if not tenant:
        log_request(req, "blocked_403", "unknown_origin", body_len)
        return JSONResponse({"error": "등록되지 않은 도메인"}, status_code=403)

    if not rate_limit_check(origin, tenant["rate_limit"]):
        log_request(req, "blocked_429", "rate_limit", body_len)
        return JSONResponse({"error": "호출 한도 초과"}, status_code=429)

    log_request(req, "ok", None, body_len)

    try:
        payload = json.loads(body.decode("utf-8")) if body else {}
        prompt = payload.get("prompt", "")
        if not prompt:
            return JSONResponse({"error": "prompt 필드가 필요합니다."}, status_code=400)
        result = await call_gemini(tenant, prompt)
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": f"Gemini 호출 실패: {e}"}, status_code=502)

# ── (개발용) 로그 조회 ─────────────────────────────────────────
@app.get("/api/logs")
async def logs(req: Request, limit: int = 50):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ts, origin, ip, user_agent, verdict, reason FROM request_logs "
                "WHERE verdict != 'ok' ORDER BY ts DESC LIMIT %s",
                (min(limit, 200),),
            )
            return {"blocked": cur.fetchall()}
    finally:
        conn.close()
