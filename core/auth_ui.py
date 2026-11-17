"""账户登录/注册 UI（侧边栏）与登录状态检查。"""

from __future__ import annotations

import streamlit as st

from core import account_service


def render_auth_sidebar() -> None:
    """在侧边栏渲染登录/注册（或已登录状态）。"""
    with st.sidebar:
        st.divider()
        user = st.session_state.get("user")

        if user:
            st.markdown(f"### 👤 {user['username']}")
            st.caption(f"账号：{user['account']}")
            if st.button("🚪 退出登录", use_container_width=True):
                st.session_state.pop("user", None)
                st.rerun()
            return

        # 未登录：登录/注册切换
        if "auth_mode" not in st.session_state:
            st.session_state["auth_mode"] = "登录"
        st.radio("账户", ["登录", "注册"], key="auth_mode", horizontal=True)

        if st.session_state["auth_mode"] == "登录":
            account = st.text_input("账号", key="login_account")
            password = st.text_input("密码", type="password", key="login_password")
            if st.button("🔐 登录", type="primary", use_container_width=True):
                u = account_service.login(account, password)
                if u:
                    st.session_state["user"] = u
                    st.success(f"欢迎回来，{u['username']}！")
                    st.rerun()
                else:
                    st.error("账号或密码错误（或被禁用）")
        else:
            username = st.text_input("用户名", key="reg_username")
            account = st.text_input("账号", key="reg_account")
            password = st.text_input("密码", type="password", key="reg_password", help="至少 6 位")
            if st.button("📝 注册", type="primary", use_container_width=True):
                ok, msg = account_service.register(username, account, password)
                if ok:
                    st.success(msg)
                    st.session_state["auth_mode"] = "登录"
                    st.rerun()
                else:
                    st.error(msg)


def require_login() -> None:
    """页面级登录检查。

    本地存在账户库（accounts.db）时要求登录；部署版无账户库则访客放行。
    """
    if not account_service.account_exists():
        return  # 访客模式（部署版）
    if not st.session_state.get("user"):
        st.warning("🔒 请先在首页侧边栏「登录 / 注册」后使用本站。")
        st.stop()
