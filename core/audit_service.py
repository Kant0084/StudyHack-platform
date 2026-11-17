"""用户输入审计日志（安全与合规审查）。

记录用户在网站上的输入内容（文本输入、上传文件元信息），供管理员后台审查。
存储复用账户服务的双模式：Supabase 优先，本地 SQLite 兜底。
"""

from __future__ import annotations

from datetime import datetime

from core import account_service as ac


def init_db() -> None:
    """初始化审计日志表（幂等）。"""
    conn, cur, is_pg = ac._connect()
    if is_pg:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                user_account TEXT,
                page TEXT,
                action TEXT,
                content TEXT,
                created_at TEXT
            )
            """
        )
    else:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_account TEXT,
                page TEXT,
                action TEXT,
                content TEXT,
                created_at TEXT
            )
            """
        )
    conn.commit()
    ac._close(conn, cur)


def log(user_account: str, page: str, action: str, content: str) -> None:
    """写入一条审计日志。content 为输入内容（文本或文件元信息）。"""
    try:
        init_db()
        conn, cur, is_pg = ac._connect()
        ph = ac._ph(is_pg)
        cur.execute(
            f"INSERT INTO audit_logs (user_account, page, action, content, created_at) "
            f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph})",
            (user_account or "访客", page, action, content,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
        ac._close(conn, cur)
    except Exception:  # noqa: BLE001
        # 审计记录失败不阻断主流程
        pass


def list_logs(limit: int = 500) -> list[dict]:
    """按时间倒序返回最近 N 条审计日志。"""
    init_db()
    conn, cur, is_pg = ac._connect()
    if is_pg:
        cur.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT %s", (limit,))
    else:
        cur.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    ac._close(conn, cur)
    return [dict(r) for r in rows]


def current_user(session_state) -> str:
    """从 st.session_state 取当前登录账号，未登录返回「访客」。"""
    user = session_state.get("user") if session_state is not None else None
    return user["account"] if user else "访客"
