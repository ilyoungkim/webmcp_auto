# ============================================================================
# webmcp/dashboard/db.py — DB 접속 및 쿼리 헬퍼
# ============================================================================
# backend/app.py 와 동일한 DB 접속 정보를 사용합니다.
# .env 파일에서 DB_HOST / DB_USER / DB_PASSWORD / DB_NAME 을 읽습니다.
# ============================================================================
import os

import pymysql
import pymysql.cursors
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "192.168.31.136")
DB_USER = os.getenv("DB_USER", "fortune")
DB_PASSWORD = os.getenv("DB_PASSWORD", "user!1234@abcd")
DB_NAME = os.getenv("DB_NAME", "webmcp")


def get_conn():
    """DB 커넥션을 반환합니다. (DictCursor, autocommit)"""
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def query(sql, params=None):
    """SELECT 쿼리를 실행하고 결과 리스트를 반환합니다."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    finally:
        conn.close()


def query_one(sql, params=None):
    """SELECT 쿼리를 실행하고 단일 행을 반환합니다. (없으면 None)"""
    rows = query(sql, params)
    return rows[0] if rows else None


def set_tenant_enabled(tenant_id, enabled):
    """테넌트의 enabled(활성/비활성) 상태를 변경합니다."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE tenants SET enabled=%s WHERE id=%s",
                (1 if enabled else 0, tenant_id),
            )
            return cur.rowcount > 0
    finally:
        conn.close()


def set_tenant_rate_limit(tenant_id, rate_limit):
    """테넌트의 rate_limit(분당 호출 한도)을 변경합니다."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE tenants SET rate_limit=%s WHERE id=%s",
                (int(rate_limit), tenant_id),
            )
            return cur.rowcount > 0
    finally:
        conn.close()


def set_tenant_tier(tenant_id, tier):
    """테넌트의 tier(등급)를 변경합니다."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE tenants SET tier=%s WHERE id=%s",
                (tier, tenant_id),
            )
            return cur.rowcount > 0
    finally:
        conn.close()


def set_tenant_model(tenant_id, model_name):
    """테넌트의 model_name(Gemini 모델)을 변경합니다."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE tenants SET model_name=%s WHERE id=%s",
                (model_name, tenant_id),
            )
            return cur.rowcount > 0
    finally:
        conn.close()


def set_tenant_password(tenant_id, password_hash):
    """테넌트의 로그인 비밀번호(SHA-256 해시)를 설정/변경합니다."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE tenants SET password=%s WHERE id=%s",
                (password_hash, tenant_id),
            )
            return cur.rowcount > 0
    finally:
        conn.close()
