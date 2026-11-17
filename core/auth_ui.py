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
            if st.button("🚪 退出登录", width="stretch"):
                st.session_state.pop("user", None)
                st.rerun()
            return

        # 未登录：用两个按钮切换「登录 / 注册」（auth_mode 为普通变量，非控件 key）
        mode = st.session_state.get("auth_mode", "登录")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔐 登录", width="stretch",
                         type="primary" if mode == "登录" else "secondary"):
                st.session_state["auth_mode"] = "登录"
                st.rerun()
        with c2:
            if st.button("📝 注册", width="stretch",
                         type="primary" if mode == "注册" else "secondary"):
                st.session_state["auth_mode"] = "注册"
                st.rerun()

        if mode == "登录":
            account = st.text_input("账号", key="login_account")
            password = st.text_input("密码", type="password", key="login_password")
            if st.button("确认登录", type="primary", width="stretch"):
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
            if st.button("确认注册", type="primary", width="stretch"):
                ok, msg = account_service.register(username, account, password)
                if ok:
                    st.success(msg)
                    st.session_state["auth_mode"] = "登录"  # 注册成功自动切回登录
                    st.rerun()
                else:
                    st.error(msg)


def require_login() -> None:
    """页面级登录检查。

    本地存在账户库（accounts.db 或 Supabase 已配置）时要求登录；否则访客放行。
    """
    if not account_service.account_exists():
        return  # 访客模式（部署版未配数据库）
    if not st.session_state.get("user"):
        st.warning("🔒 请先在首页侧边栏「登录 / 注册」后使用本站。")
        st.stop()
