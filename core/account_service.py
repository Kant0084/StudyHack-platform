"""账户管理服务（本地 SQLite 存储）。

账户数据仅存于本地 `accounts.db`，绝不部署到 GitHub / Streamlit。
密码使用 PBKDF2-HMAC-SHA256 加盐哈希，不存明文。

字段：用户名（username）、账号（account，唯一）、密码（password）。
"""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path

# 数据库文件：位于项目根目录（本地），由 .gitignore 排除，不进入版本库
DB_PATH = Path(__file__).resolve().parent.parent / "accounts.db"

_ITERATIONS = 100_000


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """初始化数据表（幂等）。"""
    conn = _connect()
    conn.execute(
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
    conn.close()


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), _ITERATIONS
    ).hex()


def account_exists() -> bool:
    """本地账户数据库是否存在（用于部署版访客模式降级判断）。"""
    return DB_PATH.exists()


# ---- 账户操作 ----

def register(username: str, account: str, password: str) -> tuple[bool, str]:
    """注册新账户。返回 (是否成功, 提示信息)。"""
    username = (username or "").strip()
    account = (account or "").strip()
    password = password or ""
    if not username or not account or not password:
        return False, "用户名、账号、密码均不能为空"
    if len(password) < 6:
        return False, "密码至少需要 6 位"
    init_db()
    salt = secrets.token_hex(16)
    h = _hash(password, salt)
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO accounts (username, account, salt, password_hash, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (username, account, salt, h, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
        return True, "注册成功，请登录"
    except sqlite3.IntegrityError:
        return False, "该账号已被注册，请更换账号"
    finally:
        conn.close()


def login(account: str, password: str) -> dict | None:
    """登录校验。成功返回用户信息 dict，失败返回 None。"""
    init_db()
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM accounts WHERE account = ?", ((account or "").strip(),)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    if row["status"] != "active":
        return None  # 被禁用
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
    """列出所有账户（不含盐/哈希）。"""
    init_db()
    conn = _connect()
    rows = conn.execute(
        "SELECT id, username, account, status, created_at FROM accounts ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_account(account: str) -> None:
    conn = _connect()
    conn.execute("DELETE FROM accounts WHERE account = ?", (account,))
    conn.commit()
    conn.close()


def set_status(account: str, status: str) -> None:
    """启用(active) / 禁用(disabled)账户。"""
    conn = _connect()
    conn.execute("UPDATE accounts SET status = ? WHERE account = ?", (status, account))
    conn.commit()
    conn.close()


def reset_password(account: str, new_password: str) -> tuple[bool, str]:
    if len(new_password or "") < 6:
        return False, "新密码至少需要 6 位"
    salt = secrets.token_hex(16)
    h = _hash(new_password, salt)
    conn = _connect()
    conn.execute("UPDATE accounts SET salt = ?, password_hash = ? WHERE account = ?", (salt, h, account))
    conn.commit()
    conn.close()
    return True, "密码已重置"
