"""用户输入审计日志（安全与合规审查）。

记录用户在网站上的输入内容：文本输入（完整）、上传文件的元信息与完整内容
（转 CSV 文本存档）。存储复用账户服务的双模式：Supabase 优先，本地 SQLite 兜底。
"""

from __future__ import annotations

from datetime import datetime

from core import account_service as ac


def mask_key(key: str) -> str:
    """API Key 掩码：仅保留前 6 位 + 后 4 位，中间以 … 隐藏（后台列表展示用）。"""
    key = (key or "").strip()
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return f"{key[:6]}…{key[-4:]}"


def init_db() -> None:
    """初始化审计日志表（幂等，含旧表自动迁移）。"""
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
                file_content TEXT,
                created_at TEXT
            )
            """
        )
        # 迁移：旧表补 file_content / api_key 列
        cur.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS file_content TEXT")
        cur.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS api_key TEXT")
    else:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_account TEXT,
                page TEXT,
                action TEXT,
                content TEXT,
                file_content TEXT,
                created_at TEXT
            )
            """
        )
        cols = [r[1] for r in cur.execute("PRAGMA table_info(audit_logs)").fetchall()]
        if "file_content" not in cols:
            cur.execute("ALTER TABLE audit_logs ADD COLUMN file_content TEXT")
        if "api_key" not in cols:
            cur.execute("ALTER TABLE audit_logs ADD COLUMN api_key TEXT")
    conn.commit()
    ac._close(conn, cur)


def log(user_account: str, page: str, action: str, content: str, file_content: str | None = None, api_key: str | None = None) -> None:
    """写入一条审计日志。content 为摘要（API Key 用掩码），api_key 存完整 Key（仅后台点开可见）。"""
    try:
        init_db()
        conn, cur, is_pg = ac._connect()
        ph = ac._ph(is_pg)
        cur.execute(
            f"INSERT INTO audit_logs (user_account, page, action, content, file_content, api_key, created_at) "
            f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
            (user_account or "访客", page, action, content, file_content, api_key,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
        ac._close(conn, cur)
    except Exception:  # noqa: BLE001
        # 审计记录失败不阻断主流程
        pass


def list_logs(limit: int = 500) -> list[dict]:
    """按时间倒序返回最近 N 条审计日志（含 file_content）。"""
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
