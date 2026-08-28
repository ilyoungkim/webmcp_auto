# ============================================================================
# webmcp/dashboard/site.py — 개인별(도메인별) 로그인 대시보드 (Streamlit)
# ============================================================================
# origin(도메인) 주소를 중심으로 로그인하여, 해당 테넌트의 정보와
# 요청 로그만 확인할 수 있는 개인별 화면입니다.
#
# 실행 방법:
#   cd webmcp/dashboard
#   streamlit run site.py
#
# 로그인 방식:
#   - tenants 테이블의 origin(도메인) + password(비밀번호) 로 로그인
#   - password 컬럼이 없거나 비어 있으면 로그인 불가 (관리자가 설정 필요)
#   - 로그인 성공 시 해당 origin 의 테넌트 정보와 요청 로그만 표시
# ============================================================================
import hashlib

import pandas as pd
import plotly.express as px
import streamlit as st

import db

st.set_page_config(
    page_title="WebMCP 개인 대시보드",
    page_icon="🔐",
    layout="wide",
)

# ── 세션 상태 초기화 ───────────────────────────────────────────
if "site_logged_in" not in st.session_state:
    st.session_state["site_logged_in"] = False
if "site_origin" not in st.session_state:
    st.session_state["site_origin"] = None
if "site_tenant" not in st.session_state:
    st.session_state["site_tenant"] = None


# ── 비밀번호 해시 (SHA-256) ─────────────────────────────────────
def hash_password(pw: str) -> str:
    """비밀번호를 SHA-256 해시로 변환합니다."""
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


# ── 테넌트 조회 ────────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_tenant_by_origin(origin: str):
    """origin(도메인)으로 테넌트를 조회합니다."""
    return db.query_one("SELECT * FROM tenants WHERE origin=%s", (origin,))


@st.cache_data(ttl=30)
def load_tenant_logs(origin: str, limit=1000):
    """특정 origin 의 요청 로그를 조회합니다."""
    return db.query(
        "SELECT * FROM request_logs WHERE origin=%s ORDER BY ts DESC LIMIT %s",
        (origin, limit),
    )


@st.cache_data(ttl=30)
def load_tenant_summary(origin: str):
    """특정 origin 의 요청 요약 통계를 조회합니다."""
    return db.query_one(
        """
        SELECT
            COUNT(*) AS total,
            SUM(verdict = 'ok') AS ok_count,
            SUM(verdict != 'ok') AS blocked_count,
            COUNT(DISTINCT ip) AS ip_count,
            MIN(ts) AS first_ts,
            MAX(ts) AS last_ts
        FROM request_logs
        WHERE origin=%s
        """,
        (origin,),
    )


# ══════════════════════════════════════════════════════════════
# 로그인 화면
# ══════════════════════════════════════════════════════════════
if not st.session_state["site_logged_in"]:
    st.title("🔐 WebMCP 개인 대시보드")
    st.caption("도메인(origin) 주소와 비밀번호로 로그인하면 해당 사이트의 정보와 로그를 확인할 수 있습니다.")

    with st.form("site_login_form"):
        origin = st.text_input(
            "도메인 주소 (origin)",
            placeholder="예: https://www.saengsaenghospital.com",
        )
        password = st.text_input(
            "비밀번호",
            type="password",
            placeholder="테넌트 비밀번호",
        )
        submitted = st.form_submit_button("🔐 로그인", type="primary")

    if submitted:
        origin = (origin or "").strip()
        if not origin or not password:
            st.error("도메인 주소와 비밀번호를 모두 입력해 주세요.")
        else:
            tenant = load_tenant_by_origin(origin)
            if not tenant:
                st.error("등록되지 않은 도메인입니다. 관리자에게 문의하세요.")
            elif not tenant.get("password"):
                st.warning("이 도메인은 아직 로그인 비밀번호가 설정되지 않았습니다. 관리자에게 문의하세요.")
            elif tenant["password"] != hash_password(password):
                st.error("비밀번호가 올바르지 않습니다.")
            else:
                st.session_state["site_logged_in"] = True
                st.session_state["site_origin"] = origin
                st.session_state["site_tenant"] = tenant
                st.rerun()

    st.stop()

# ══════════════════════════════════════════════════════════════
# 로그인 성공 후 — 개인 대시보드
# ══════════════════════════════════════════════════════════════
tenant = st.session_state["site_tenant"]
origin = st.session_state["site_origin"]

# ── 사이드바 ────────────────────────────────────────────────────
st.sidebar.title("🔐 개인 대시보드")
st.sidebar.markdown(f"**{origin}**")
st.sidebar.caption(f"site_ns: {tenant['site_ns']}")
if st.sidebar.button("🚪 로그아웃"):
    st.session_state["site_logged_in"] = False
    st.session_state["site_origin"] = None
    st.session_state["site_tenant"] = None
    st.rerun()

# ── 상단 제목 ──────────────────────────────────────────────────
st.title(f"🏢 {origin}")
st.caption("이 도메인(테넌트)의 설정 정보와 요청 로그를 확인합니다.")

# ── 테넌트 정보 카드 ───────────────────────────────────────────
st.subheader("📋 테넌트 정보")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("상태", "🟢 활성" if tenant["enabled"] else "🔴 비활성")
c2.metric("분당 호출 한도", f"{tenant['rate_limit']}")
c3.metric("등급 (tier)", tenant["tier"])
c4.metric("모델", tenant["model_name"])
c5.metric("site_ns", tenant["site_ns"])

# ── 요청 요약 ───────────────────────────────────────────────────
summary = load_tenant_summary(origin)
if summary:
    st.subheader("📊 요청 요약")
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("총 요청", f"{summary['total'] or 0:,}")
    s2.metric("정상 요청", f"{summary['ok_count'] or 0:,}")
    s3.metric("차단 요청", f"{summary['blocked_count'] or 0:,}")
    s4.metric("고유 IP", f"{summary['ip_count'] or 0:,}")
    st.caption(f"기간: {summary['first_ts']} ~ {summary['last_ts']}")

# ── 요청 로그 ──────────────────────────────────────────────────
st.subheader("📜 요청 로그")
logs = load_tenant_logs(origin)
if not logs:
    st.info("이 도메인의 요청 로그가 아직 없습니다.")
else:
    df = pd.DataFrame(logs)

    # 시간대별 요청 수
    df["ts"] = pd.to_datetime(df["ts"])
    df["minute"] = df["ts"].dt.floor("min")
    hourly = (
        df.groupby("minute")
        .size()
        .reset_index(name="count")
        .sort_values("minute")
    )
    st.plotly_chart(
        px.line(hourly, x="minute", y="count", markers=True, title="요청 추이 (분 단위)"),
        width='stretch',
    )

    # verdict 분포
    verdict_counts = df["verdict"].fillna("ok").value_counts().reset_index()
    verdict_counts.columns = ["verdict", "count"]
    st.plotly_chart(
        px.pie(verdict_counts, names="verdict", values="count", title="요청 상태(verdict) 분포"),
        width='stretch',
    )

    # IP별 요청 수
    st.subheader("IP별 요청 수")
    ip_counts = (
        df["ip"].fillna("(없음)").value_counts().head(20).reset_index()
    )
    ip_counts.columns = ["ip", "count"]
    st.plotly_chart(
        px.bar(ip_counts, x="ip", y="count", orientation="h", title="IP별 요청 수"),
        width='stretch',
    )

    # 차단 로그
    blocked = df[df["verdict"] != "ok"]
    if not blocked.empty:
        st.subheader("🚫 차단 로그")
        st.dataframe(blocked, width='stretch')

    # 전체 로그
    st.subheader("전체 로그")
    st.dataframe(df, width='stretch')

st.sidebar.markdown("---")
st.sidebar.caption("WebMCP 개인 대시보드 · Streamlit")
