"""Simple password authentication for Streamlit web UI."""

from __future__ import annotations

import hashlib
import os
import secrets
from pathlib import Path

import streamlit as st

_AUTH_ENABLED: bool | None = None
_PASSWORD_HASH: str | None = None
_SESSION_TOKEN: str | None = None


def _get_auth_dir() -> Path:
    """Get data directory for storing auth credentials."""
    home = Path.home()
    auth_dir = home / ".tradingagents"
    auth_dir.mkdir(parents=True, exist_ok=True)
    return auth_dir


def _get_password_file() -> Path:
    """Path to stored password hash file."""
    return _get_auth_dir() / ".web_password_hash"


def _get_session_file() -> Path:
    """Path to stored session token."""
    return _get_auth_dir() / ".web_session"


def is_auth_enabled() -> bool:
    """Check if authentication is enabled via ADMIN_AUTH_ENABLED env var."""
    global _AUTH_ENABLED
    if _AUTH_ENABLED is not None:
        return _AUTH_ENABLED
    _AUTH_ENABLED = os.environ.get("ADMIN_AUTH_ENABLED", "").strip().lower() in ("true", "1", "yes")
    return _AUTH_ENABLED


def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, bytes]:
    """Hash password with PBKDF2-SHA256. Returns (hash_hex, salt)."""
    if salt is None:
        salt = secrets.token_bytes(32)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return hashed.hex(), salt


def _verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored hash."""
    try:
        salt_hex, hash_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_hash, _ = _hash_password(password, salt)
        return secrets.compare_digest(expected_hash, hash_hex)
    except (ValueError, AttributeError):
        return False


def has_stored_password() -> bool:
    """Check if a password has been set (via file or env var)."""
    if is_auth_enabled():
        if os.environ.get("ADMIN_PASSWORD"):
            return True
        pwd_file = _get_password_file()
        if pwd_file.exists():
            try:
                content = pwd_file.read_text().strip()
                return bool(content and ":" in content)
            except OSError:
                pass
    return False


def _get_env_password_hash() -> str | None:
    """Get password hash from ADMIN_PASSWORD env var (plaintext, not hashed for simplicity)."""
    return os.environ.get("ADMIN_PASSWORD") or None


def _get_file_password_hash() -> str | None:
    """Get password hash from password file."""
    pwd_file = _get_password_file()
    if pwd_file.exists():
        try:
            content = pwd_file.read_text().strip()
            if content and ":" in content:
                return content
        except OSError:
            pass
    return None


def get_session_token() -> str | None:
    """Get current session token from file."""
    if is_auth_enabled():
        try:
            session_file = _get_session_file()
            if session_file.exists():
                return session_file.read_text().strip()
        except OSError:
            pass
    return None


def set_session_token(token: str) -> None:
    """Save session token to file."""
    try:
        session_file = _get_session_file()
        session_file.write_text(token)
    except OSError:
        pass


def clear_session_token() -> None:
    """Remove session token file."""
    try:
        session_file = _get_session_file()
        if session_file.exists():
            session_file.unlink()
    except OSError:
        pass


def verify_session(request_token: str | None) -> bool:
    """Verify if the request token matches stored session."""
    if not request_token:
        return False
    stored = get_session_token()
    if not stored:
        return False
    return secrets.compare_digest(request_token, stored)


def set_password(password: str) -> str | None:
    """Set initial password. Returns error message or None on success."""
    if not password:
        return "密码不能为空"
    if len(password) < 4:
        return "密码长度至少4位"

    hashed, salt = _hash_password(password)
    stored_value = f"{salt.hex()}:{hashed}"

    try:
        pwd_file = _get_password_file()
        pwd_file.write_text(stored_value)
        return None
    except OSError:
        return "密码保存失败"


def change_password(current_password: str, new_password: str) -> str | None:
    """Change password. Returns error message or None on success."""
    if not current_password:
        return "请输入当前密码"
    if not new_password:
        return "请输入新密码"
    if len(new_password) < 4:
        return "新密码长度至少4位"

    if _get_env_password_hash() is not None:
        if not secrets.compare_digest(current_password, _get_env_password_hash()):
            return "当前密码错误"
    elif _get_file_password_hash():
        if not _verify_password(current_password, _get_file_password_hash()):
            return "当前密码错误"

    if os.environ.get("ADMIN_PASSWORD"):
        return "通过环境变量配置的密码无法在此修改，请更新.env文件中的ADMIN_PASSWORD"

    err = set_password(new_password)
    if err:
        return err

    new_token = secrets.token_urlsafe(32)
    set_session_token(new_token)
    return None


def verify_login(password: str) -> bool:
    """Verify login password."""
    if not is_auth_enabled():
        return True
    if not has_stored_password():
        return False

    env_password = _get_env_password_hash()
    if env_password is not None:
        return secrets.compare_digest(password, env_password)

    file_hash = _get_file_password_hash()
    if file_hash:
        return _verify_password(password, file_hash)

    return False


def check_auth() -> bool:
    """Check if current session is authenticated."""
    if not is_auth_enabled():
        return True
    token = st.query_params.get("token", None)
    if token:
        return verify_session(token)
    if "auth_token" in st.session_state:
        return verify_session(st.session_state.get("auth_token"))
    return False


def login_user(token: str) -> None:
    """Set authenticated session."""
    st.session_state["auth_token"] = token
    set_session_token(token)
    st.query_params["token"] = token


def logout_user() -> None:
    """Clear authenticated session."""
    st.session_state.pop("auth_token", None)
    clear_session_token()
    st.query_params.pop("token", None)


def render_login_page() -> bool:
    """Render login form. Returns True if authenticated, False otherwise."""
    if check_auth():
        return True

    st.set_page_config(page_title="登录 - A股投研分析", page_icon="🔐")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🔐 登录")
        st.markdown("---")

        password = st.text_input("密码", type="password", placeholder="请输入管理员密码")

        if st.button("登录", type="primary", use_container_width=True):
            if verify_login(password):
                new_token = secrets.token_urlsafe(32)
                login_user(new_token)
                st.rerun()
            else:
                st.error("密码错误")

        st.markdown("---")
        st.caption("请联系系统管理员获取登录密码")

    return False
