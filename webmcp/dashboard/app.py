# ============================================================================
# webmcp/dashboard/app.py — WebMCP 백엔드 DB 대시보드 (Streamlit)
# ============================================================================
# DB(webmcp)에 저장된 정보를 시각화합니다.
#   - tenants  : 멀티테넌트(도메인별 Gemini 키/한도) 설정
#   - request_logs : 요청 로깅 (비정상 접속 감지/분석)
#
# 실행 방법:
#   cd webmcp/dashboard
#   streamlit run app.py
# ============================================================================
import hashlib

import pandas as pd
import plotly.express as px
import streamlit as st

import db

st.set_page_config(
    page_title="WebMCP 대시보드",
    page_icon="📊",
    layout="wide",
)

# ── 사이드바: DB 접속 상태 ─────────────────────────────────────
st.sidebar.title("📊 WebMCP 대시보드")
st.sidebar.caption("DB(webmcp)에 저장된 정보를 확인합니다.")


@st.cache_data(ttl=30)
def load_tenants():
    return db.query("SELECT * FROM tenants ORDER BY id")


@st.cache_data(ttl=30)
def load_logs(limit=5000):
    return db.query(
        "SELECT * FROM request_logs ORDER BY ts DESC LIMIT %s", (limit,)
    )


@st.cache_data(ttl=30)
def load_summary():
    return db.query_one(
        """
        SELECT
            COUNT(*) AS total,
            SUM(verdict = 'ok') AS ok_count,
            SUM(verdict != 'ok') AS blocked_count,
            COUNT(DISTINCT origin) AS origin_count,
            COUNT(DISTINCT ip) AS ip_count,
            MIN(ts) AS first_ts,
            MAX(ts) AS last_ts
        FROM request_logs
        """
    )


# ── DB 연결 확인 ───────────────────────────────────────────────
try:
    summary = load_summary()
    db_ok = True
except Exception as e:
    summary = None
    db_ok = False
    db_error = str(e)

if not db_ok:
    st.error("DB 연결에 실패했습니다.")
    st.code(db_error, language="text")
    st.info(
        "`webmcp/dashboard/.env` 파일에 DB 접속 정보가 올바른지 확인하세요. "
        "없다면 `.env.example`을 복사해 만드세요."
    )
    st.stop()

# ── 상단 KPI 카드 ──────────────────────────────────────────────
st.title("📊 WebMCP 백엔드 DB 대시보드")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("총 요청", f"{summary['total']:,}")
c2.metric("정상 요청", f"{summary['ok_count'] or 0:,}")
c3.metric("차단 요청", f"{summary['blocked_count'] or 0:,}")
c4.metric("도메인(테넌트)", f"{summary['origin_count'] or 0:,}")
c5.metric("고유 IP", f"{summary['ip_count'] or 0:,}")

st.caption(
    f"기간: {summary['first_ts']} ~ {summary['last_ts']} "
    f"(최근 30초 캐시, 새로고침 시 갱신)"
)

# ── 탭 구성 ────────────────────────────────────────────────────
# 도메인(테넌트) 설정은 가장 마지막 탭에 배치합니다.
tab1, tab2, tab3, tab4 = st.tabs(
    ["📈 요청 분석", "🚫 차단 로그", "📋 전체 로그", "🏢 테넌트 설정"]
)

# ══════════════════════════════════════════════════════════════
# TAB 1: 요청 분석
# ══════════════════════════════════════════════════════════════
with tab1:
    logs = load_logs()
    if not logs:
        st.info("아직 요청 로그가 없습니다.")
    else:
        df = pd.DataFrame(logs)

        # 시간대별 요청 수 (분 단위)
        df["ts"] = pd.to_datetime(df["ts"])
        df["minute"] = df["ts"].dt.floor("min")
        hourly = (
            df.groupby("minute")
            .size()
            .reset_index(name="count")
            .sort_values("minute")
        )

        st.subheader("시간대별 요청 수")
        fig = px.line(
            hourly,
            x="minute",
            y="count",
            markers=True,
            title="요청 추이 (분 단위)",
        )
        st.plotly_chart(fig, width='stretch')

        # verdict 별 분포
        st.subheader("요청 상태(verdict) 분포")
        verdict_counts = df["verdict"].fillna("ok").value_counts().reset_index()
        verdict_counts.columns = ["verdict", "count"]
        fig2 = px.pie(
            verdict_counts,
            names="verdict",
            values="count",
            title="verdict 분포",
        )
        st.plotly_chart(fig2, width='stretch')

        # 도메인별 요청 수 (테이블 + 월간 비교)
        st.subheader("도메인(origin)별 요청 수")
        df["origin"] = df["origin"].fillna("(없음)")

        # 월간 비교를 위해 '년월' 컬럼 추가
        df["year_month"] = df["ts"].dt.to_period("M").astype(str)

        # 도메인별 전체 요청 수 (테이블)
        origin_total = (
            df.groupby("origin")
            .size()
            .reset_index(name="전체 요청 수")
            .sort_values("전체 요청 수", ascending=False)
            .reset_index(drop=True)
        )

        # 테이블로 표시 (숫자만)
        st.markdown("**전체 요청 수 (누적)**")
        st.dataframe(origin_total, use_container_width=True, hide_index=True)

        # ── 월간 증감 비교 (최근 두 달) ──
        months = sorted(df["year_month"].unique(), reverse=True)
        st.markdown("**월간 비교 (최근 두 달)**")

        if len(months) >= 2:
            this_month = months[0]   # 최신 월
            prev_month = months[1]   # 직전 월

            pivot = (
                df.groupby(["origin", "year_month"])
                .size()
                .unstack(fill_value=0)
            )
            # 해당 월이 없는 origin 은 0 으로 보정
            for m in (this_month, prev_month):
                if m not in pivot.columns:
                    pivot[m] = 0

            cmp = pd.DataFrame(index=pivot.index)
            cmp[f"{prev_month} 요청"] = pivot[prev_month].astype(int)
            cmp[f"{this_month} 요청"] = pivot[this_month].astype(int)
            cmp["증감"] = cmp[f"{this_month} 요청"] - cmp[f"{prev_month} 요청"]
            # 증감률 (%) — 직전 월 0 이면 표시를 "-" 로
            cmp["증감률(%)"] = cmp.apply(
                lambda r: (
                    round((r["증감"] / r[f"{prev_month} 요청"]) * 100, 1)
                    if r[f"{prev_month} 요청"] > 0 else None
                ),
                axis=1,
            )
            cmp = cmp.sort_values(f"{this_month} 요청", ascending=False)

            st.caption(f"비교 기준: {prev_month} → {this_month}")
            st.dataframe(cmp, use_container_width=True)
        else:
            st.info("아직 두 달 이상의 데이터가 없어 월간 비교가 불가능합니다.")

        # IP별 요청 수 (상위 20)
        st.subheader("IP별 요청 수 (상위 20)")
        ip_counts = (
            df["ip"].fillna("(없음)").value_counts().head(20).reset_index()
        )
        ip_counts.columns = ["ip", "count"]
        fig4 = px.bar(
            ip_counts,
            x="ip",
            y="count",
            orientation="h",
            title="IP별 요청 수",
        )
        st.plotly_chart(fig4, width='stretch')

# ══════════════════════════════════════════════════════════════
# TAB 4: 테넌트 설정 (가장 마지막 탭)
# ══════════════════════════════════════════════════════════════
with tab4:
    tenants = load_tenants()
    if not tenants:
        st.info("등록된 테넌트가 없습니다.")
    else:
        # 저장 결과 메시지 표시 (rerun 후에도 유지)
        if "save_msg" in st.session_state:
            msg = st.session_state.pop("save_msg")
            if msg.startswith("✅"):
                st.success(msg)
            else:
                st.info(msg)

        st.subheader("테넌트(도메인별) 설정")
        st.caption(
            "도메인별 설정은 아래 **목록 · 요청 현황** 뒤에 위치합니다. "
            "도메인을 선택해 **사용 여부(활성/비활성) · 분당 호출 한도 · 등급(tier) · Gemini 모델**을 "
            "모두 설정할 수 있습니다."
        )

        # ── 테넌트 목록 테이블 (키 마스킹) ──────────────────────
        st.subheader("전체 테넌트 목록")
        tdf = pd.DataFrame(tenants)
        if "gemini_key" in tdf.columns:
            tdf["gemini_key"] = tdf["gemini_key"].apply(
                lambda k: (k[:6] + "…" + k[-4:]) if isinstance(k, str) and len(k) > 12 else "***"
            )
        st.dataframe(tdf, width='stretch')

        # ── 테넌트별 요청 현황 ──────────────────────────────────
        st.subheader("테넌트별 요청 현황")
        logs2 = load_logs()
        if logs2:
            df2 = pd.DataFrame(logs2)
            df2["origin"] = df2["origin"].fillna("(없음)")
            per_tenant = (
                df2.groupby("origin")
                .agg(
                    total=("id", "count"),
                    ok=("verdict", lambda s: (s == "ok").sum()),
                    blocked=("verdict", lambda s: (s != "ok").sum()),
                )
                .reset_index()
            )
            st.dataframe(per_tenant, width='stretch')

        st.divider()

        # ── 도메인별 설정 (목록 · 요청 현황 뒤에 배치) ──────────
        st.subheader("도메인별 설정")
        st.caption(
            "도메인을 선택해 하나의 화면에서 **사용 여부(활성/비활성) · 분당 호출 한도 · 등급(tier) · Gemini 모델**을 "
            "모두 설정할 수 있습니다."
        )

        # ── 설정할 테넌트 선택 ─────────────────────────────────
        tenant_options = {
            f"{t['origin']} (id:{t['id']})": t for t in tenants
        }
        selected_label = st.selectbox(
            "설정할 테넌트 선택",
            options=list(tenant_options.keys()),
            key="tenant_select",
        )
        sel = tenant_options[selected_label]

        st.markdown(
            "🟢 활성" if sel["enabled"] else "🔴 비활성",
            help="현재 상태",
        )

        # ── 통합 설정 폼 (사용 여부 + 한도 + 등급 + 모델) ───────
        with st.form(key=f"tenant_form_{sel['id']}"):
            col_a, col_b = st.columns([1, 4])
            with col_a:
                new_enabled = st.toggle(
                    "도메인 사용",
                    value=bool(sel["enabled"]),
                    help="비활성 시 해당 도메인 요청이 403 차단됩니다.",
                    key=f"enabled_{sel['id']}",
                )
            with col_b:
                st.markdown(f"**{sel['origin']}**  \n`site_ns: {sel['site_ns']}`")

            col_c, col_d, col_e = st.columns(3)
            with col_c:
                new_rate = st.number_input(
                    "분당 호출 한도 (rate_limit)",
                    min_value=1,
                    max_value=10000,
                    value=int(sel["rate_limit"]),
                    step=1,
                    key=f"rate_{sel['id']}",
                )
            with col_d:
                new_tier = st.selectbox(
                    "등급 (tier)",
                    options=["dev", "prod", "test", "beta"],
                    index=["dev", "prod", "test", "beta"].index(sel["tier"])
                    if sel["tier"] in ["dev", "prod", "test", "beta"]
                    else 0,
                    key=f"tier_{sel['id']}",
                )
            with col_e:
                # Gemini 모델 선택 (사전 정의된 모델 목록 + 사용자 지정)
                # ── 모델별 특징 (README.md "사용 가능한 Gemini 모델별 특징" 참고) ──
                #   gemini-3.1-flash-lite  : 저비용·저지연 경량 채팅 모델
                #   gemini-3.5-flash-lite  : 최신 Flash-Lite, 속도·품질 균형 (추천)
                #   gemini-2.0-flash       : 범용 멀티모달 (이미지·텍스트, 도구 호출)
                #   gemini-2.5-flash       : 추론 능력 강화된 범용 모델
                #   gemini-embedding-2     : 최신 Gemini Embedding (이미지·문서 포함, 3072차원)
                #   gemini-embedding-001   : Gemini Embedding (텍스트 전용, 3072차원)
                #   text-embedding-004     : 구형 임베딩 (2026-01 중순 지원 중단, 마이그레이션 권장)
                GEMINI_MODELS = [
                    "gemini-3.1-flash-lite",   # Gemini 3.1 Flash-Lite
                    "gemini-3.5-flash-lite",   # Gemini 3.5 Flash-Lite
                    "gemini-2.0-flash",        # Gemini 2.0 Flash
                    "gemini-2.5-flash",        # Gemini 2.5 Flash
                    "gemini-embedding-2",      # Gemini Embedding 2 (이미지·문서)
                    "gemini-embedding-001",    # Gemini Embedding (텍스트 전용)
                    "text-embedding-004",      # 구형 임베딩 (지원 중단 예정)
                ]
                # 현재 저장된 모델이 목록에 없으면 "사용자 지정" 옵션으로 표시
                model_options = GEMINI_MODELS + ["✏️ 사용자 지정"]
                current_model = sel["model_name"]
                default_index = (
                    GEMINI_MODELS.index(current_model)
                    if current_model in GEMINI_MODELS
                    else len(GEMINI_MODELS)  # "사용자 지정" 인덱스
                )
                new_model = st.selectbox(
                    "Gemini 모델 (model_name)",
                    options=model_options,
                    index=default_index,
                    key=f"model_{sel['id']}",
                )
                # "사용자 지정" 선택 시 직접 입력 가능
                if new_model == "✏️ 사용자 지정":
                    new_model = st.text_input(
                        "사용자 지정 모델명",
                        value=current_model,
                        key=f"model_custom_{sel['id']}",
                    )

            # ── 개인 대시보드 로그인 비밀번호 설정 ──────────────
            st.divider()
            st.markdown("**🔐 개인 대시보드 로그인 비밀번호**")
            st.caption(
                "이 비밀번호로 `site.py` 개인 대시보드에 로그인할 수 있습니다. "
                "비워두면 기존 비밀번호를 유지합니다."
            )
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                new_password = st.text_input(
                    "새 비밀번호",
                    type="password",
                    placeholder="설정할 비밀번호",
                    key=f"pw_{sel['id']}",
                )
            with col_p2:
                new_password2 = st.text_input(
                    "새 비밀번호 확인",
                    type="password",
                    placeholder="비밀번호 재입력",
                    key=f"pw2_{sel['id']}",
                )

            submitted = st.form_submit_button("💾 설정 저장", type="primary")

        # ── 저장 처리 (변경된 항목만 DB 반영) ───────────────────
        if submitted:
            updated = False

            if new_enabled != bool(sel["enabled"]):
                db.set_tenant_enabled(sel["id"], new_enabled)
                updated = True

            if int(new_rate) != int(sel["rate_limit"]):
                db.set_tenant_rate_limit(sel["id"], int(new_rate))
                updated = True

            if new_tier != sel["tier"]:
                db.set_tenant_tier(sel["id"], new_tier)
                updated = True

            if (new_model or "").strip() != sel["model_name"]:
                db.set_tenant_model(sel["id"], new_model.strip())
                updated = True

            # 비밀번호 변경 처리 (둘 다 입력했을 때만)
            if new_password or new_password2:
                if new_password != new_password2:
                    st.session_state["save_msg"] = "❌ 비밀번호가 일치하지 않습니다."
                    st.rerun()
                elif len(new_password) < 4:
                    st.session_state["save_msg"] = "❌ 비밀번호는 4자 이상이어야 합니다."
                    st.rerun()
                else:
                    pw_hash = hashlib.sha256(new_password.encode("utf-8")).hexdigest()
                    db.set_tenant_password(sel["id"], pw_hash)
                    updated = True

            if updated:
                # rerun 후에도 메시지가 유지되도록 session_state에 저장
                st.session_state["save_msg"] = (
                    f"✅ {sel['origin']} 설정이 저장되었습니다."
                )
                load_tenants.clear()  # 캐시 무효화
                st.rerun()
            else:
                st.session_state["save_msg"] = "ℹ️ 변경된 설정이 없습니다."
                st.rerun()

# ══════════════════════════════════════════════════════════════
# TAB 2: 차단 로그
# ══════════════════════════════════════════════════════════════
with tab2:
    blocked = db.query(
        "SELECT * FROM request_logs WHERE verdict != 'ok' ORDER BY ts DESC LIMIT 500"
    )
    if not blocked:
        st.info("차단된 요청이 없습니다. 🎉")
    else:
        bdf = pd.DataFrame(blocked)
        st.subheader("차단된 요청 (최근 500건)")
        st.dataframe(bdf, width='stretch')

        st.subheader("차단 사유(reason) 분포")
        reason_counts = (
            bdf["reason"].fillna("(없음)").value_counts().reset_index()
        )
        reason_counts.columns = ["reason", "count"]
        fig5 = px.bar(
            reason_counts,
            x="reason",
            y="count",
            title="차단 사유 분포",
        )
        st.plotly_chart(fig5, width='stretch')

# ══════════════════════════════════════════════════════════════
# TAB 3: 전체 로그
# ══════════════════════════════════════════════════════════════
with tab3:
    all_logs = load_logs(limit=1000)
    if not all_logs:
        st.info("로그가 없습니다.")
    else:
        adf = pd.DataFrame(all_logs)
        st.subheader("전체 요청 로그 (최근 1000건)")
        st.dataframe(adf, width='stretch')

st.sidebar.markdown("---")
st.sidebar.caption("WebMCP 백엔드 DB 대시보드 · Streamlit")
