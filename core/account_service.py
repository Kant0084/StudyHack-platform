"""账户管理服务（双模式存储：Supabase/Postgres 优先，本地 SQLite 兜底）。

- 配置了 `SUPABASE_DB_URL`（环境变量 或 Streamlit Secrets）→ 用 Supabase Postgres，
  账户数据上云，部署版与本地后台共享同一份账户数据；
- 未配置 → 用本地 SQLite（`accounts.db`），仅本地可用（部署版自动降级访客模式）。

密码使用 PBKDF2-HMAC-SHA256 加盐哈希，不存明文。
"""

from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path

# 本地 SQLite 数据库（仅在未配置 Supabase 时使用），由 .gitignore 排除
DB_PATH = Path(__file__).resolve().parent.parent / "accounts.db"

_ITERATIONS = 100_000


# ---- 连接串获取 ----

# 占位符标记：密码尚未替换时，视为「未配置」，自动降级本地 SQLite
_PLACEHOLDER_MARKS = ("你的数据库密码", "[YOUR-PASSWORD]", "[YOUR_PASSWORD]", "your_password", "占位")


def _is_placeholder(url: str) -> bool:
    return any(mark in url for mark in _PLACEHOLDER_MARKS)


def _norm_account(account: str) -> str:
    """账号统一归一化：去首尾空白 + 转小写（登录/注册大小写不敏感）。"""
    return (account or "").strip().lower()


def _db_url() -> str | None:
    """优先环境变量，其次 Streamlit Secrets，返回 Supabase Postgres 连接串。

    密码仍为占位符时视为未配置，返回 None（降级本地 SQLite）。
    """
    url = os.environ.get("SUPABASE_DB_URL")
    if url and not _is_placeholder(url):
        return url.strip()
    try:
        import streamlit as st

        url = st.secrets.get("SUPABASE_DB_URL")
        if url and not _is_placeholder(str(url)):
            return str(url).strip()
    except Exception:  # noqa: BLE001
        pass
    return None


def _use_pg() -> bool:
    return _db_url() is not None


def _ph(is_pg: bool) -> str:
    return "%s" if is_pg else "?"


def _connect():
    """返回 (conn, cursor, is_pg)。"""
    url = _db_url()
    if url:
        import psycopg2
        import psycopg2.extras

        conn = psycopg2.connect(url)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return conn, cur, True
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn, conn.cursor(), False


def _close(conn, cur) -> None:
    try:
        cur.close()
    except Exception:  # noqa: BLE001
        pass
    conn.close()


def _is_unique_violation(exc, is_pg: bool) -> bool:
    if is_pg:
        code = getattr(exc, "pgcode", None)
        return code == "23505"
    return isinstance(exc, sqlite3.IntegrityError)


def init_db() -> None:
    """初始化数据表（幂等）。"""
    conn, cur, is_pg = _connect()
    if is_pg:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL,
                account TEXT NOT NULL UNIQUE,
                salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL
            )
            """
        )
    else:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                account TEXT NOT NULL UNIQUE,
                salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL
            )
            """
        )
    conn.commit()
    _close(conn, cur)


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), _ITERATIONS
    ).hex()


def account_exists() -> bool:
    """账户库是否可用（Supabase 已配置，或本地库存在）。"""
    return _use_pg() or DB_PATH.exists()


# ---- 账户操作 ----

def register(username: str, account: str, password: str) -> tuple[bool, str]:
    username = (username or "").strip()
    account = _norm_account(account)
    password = password or ""
    if not username or not account or not password:
        return False, "用户名、账号、密码均不能为空"
    if len(password) < 6:
        return False, "密码至少需要 6 位"
    init_db()
    salt = secrets.token_hex(16)
    h = _hash(password, salt)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn, cur, is_pg = _connect()
    ph = _ph(is_pg)
    try:
        cur.execute(
            f"INSERT INTO accounts (username, account, salt, password_hash, created_at) "
            f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph})",
            (username, account, salt, h, now),
        )
        conn.commit()
        return True, "注册成功，请登录"
    except Exception as exc:  # noqa: BLE001
        if _is_unique_violation(exc, is_pg):
            return False, "该账号已被注册，请更换账号"
        raise
    finally:
        _close(conn, cur)


def login(account: str, password: str) -> dict | None:
    init_db()
    conn, cur, is_pg = _connect()
    ph = _ph(is_pg)
    try:
        cur.execute(f"SELECT * FROM accounts WHERE account = {ph}", (_norm_account(account),))
        row = cur.fetchone()
        row = dict(row) if row else None
    finally:
        _close(conn, cur)

    if row is None:
        return None
    if row["status"] != "active":
        return None
    if _hash(password or "", row["salt"]) != row["password_hash"]:
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "account": row["account"],
        "status": row["status"],
        "created_at": row["created_at"],
    }


# ---- 管理操作（后台专用）----

def list_accounts() -> list[dict]:
    init_db()
    conn, cur, is_pg = _connect()
    cur.execute("SELECT id, username, account, status, created_at FROM accounts ORDER BY id DESC")
    rows = cur.fetchall()
    _close(conn, cur)
    return [dict(r) for r in rows]


def delete_account(account: str) -> None:
    conn, cur, is_pg = _connect()
    ph = _ph(is_pg)
    cur.execute(f"DELETE FROM accounts WHERE account = {ph}", (_norm_account(account),))
    conn.commit()
    _close(conn, cur)


def set_status(account: str, status: str) -> None:
    conn, cur, is_pg = _connect()
    ph = _ph(is_pg)
    cur.execute(f"UPDATE accounts SET status = {ph} WHERE account = {ph}", (status, _norm_account(account)))
    conn.commit()
    _close(conn, cur)


def reset_password(account: str, new_password: str) -> tuple[bool, str]:
    if len(new_password or "") < 6:
        return False, "新密码至少需要 6 位"
    salt = secrets.token_hex(16)
    h = _hash(new_password, salt)
    conn, cur, is_pg = _connect()
    ph = _ph(is_pg)
    cur.execute(
        f"UPDATE accounts SET salt = {ph}, password_hash = {ph} WHERE account = {ph}",
        (salt, h, _norm_account(account)),
    )
    conn.commit()
    _close(conn, cur)
    return True, "密码已重置"
