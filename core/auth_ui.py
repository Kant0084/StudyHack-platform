"""账户登录/注册 UI（侧边栏）与登录状态检查。"""

from __future__ import annotations

import streamlit as st

from core import account_service


def _switch_login() -> None:
    st.session_state["auth_mode"] = "登录"


def _switch_register() -> None:
    st.session_state["auth_mode"] = "注册"


def _submit_register() -> None:
    """注册回调（在控件实例化前运行，安全修改 session_state）。"""
    ok, msg = account_service.register(
        st.session_state.get("reg_username", ""),
        st.session_state.get("reg_account", ""),
        st.session_state.get("reg_password", ""),
    )
    if ok:
        st.session_state["auth_mode"] = "登录"
    st.session_state["register_msg"] = ("success" if ok else "error", msg)


def _show_register_msg() -> None:
    """展示注册结果消息（只展示一次）。"""
    msg = st.session_state.pop("register_msg", None)
    if msg:
        kind, text = msg
        (st.success if kind == "success" else st.error)(text)


def render_auth_sidebar() -> None:
    """在侧边栏渲染登录/注册（或已登录状态）。"""
    with st.sidebar:
        st.divider()
        user = st.session_state.get("user")

        if user:
            st.markdown(f"### 👤 {user['username']}")
            st.caption(f"账号：{user['account']}")
            if st.button("🚪 退出登录", width="stretch"):
                st.session_state.pop("user", None)
                st.rerun()
            return

        # 未登录：两个按钮切换「登录 / 注册」（on_click 回调，规避控件键冲突）
        mode = st.session_state.get("auth_mode", "登录")
        c1, c2 = st.columns(2)
        with c1:
            st.button("🔐 登录", width="stretch",
                      type="primary" if mode == "登录" else "secondary",
                      on_click=_switch_login)
        with c2:
            st.button("📝 注册", width="stretch",
                      type="primary" if mode == "注册" else "secondary",
                      on_click=_switch_register)

        if mode == "登录":
            _show_register_msg()
            account = st.text_input("账号", key="login_account")
            password = st.text_input("密码", type="password", key="login_password")
            if st.button("确认登录", type="primary", width="stretch"):
                u = account_service.login(account, password)
                if u:
                    st.session_state["user"] = u
                    st.rerun()
                else:
                    st.error("账号或密码错误（或被禁用）")
        else:
            username = st.text_input("用户名", key="reg_username")
            account = st.text_input("账号", key="reg_account")
            password = st.text_input("密码", type="password", key="reg_password", help="至少 6 位")
            st.button("确认注册", type="primary", width="stretch", on_click=_submit_register)
            _show_register_msg()


def require_login() -> None:
    """页面级登录检查。

    本地存在账户库（accounts.db 或 Supabase 已配置）时要求登录；否则访客放行。
    """
    if not account_service.account_exists():
        return  # 访客模式（部署版未配数据库）
    if not st.session_state.get("user"):
        st.warning("🔒 请先在左侧边栏「登录 / 注册」后使用本站。")
        st.stop()
