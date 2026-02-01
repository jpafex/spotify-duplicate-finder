import streamlit as st
from .cookies import get_cookies
from .config import AUTH_COOKIE_KEY

def is_logged_in() -> bool:
    cookies = get_cookies()

    # Restore session login from cookie if session was reset by redirect
    if not st.session_state.get("password_correct"):
        if cookies.get(AUTH_COOKIE_KEY) == "1":
            st.session_state["password_correct"] = True

    return bool(st.session_state.get("password_correct"))

def require_login() -> None:
    """
    Shows login form and stops page execution until authenticated.
    """
    if is_logged_in():
        return

    cookies = get_cookies()
    st.title("🔐 AfexCloud Tool Login")

    with st.form("login_form"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if u == st.secrets["APP_USER"] and p == st.secrets["APP_PASS"]:
                st.session_state["password_correct"] = True
                cookies[AUTH_COOKIE_KEY] = "1"
                cookies.save()
                st.rerun()
            else:
                st.error("Invalid credentials.")

    st.stop()

def logout() -> None:
    cookies = get_cookies()
    st.session_state["password_correct"] = False
    try:
        if AUTH_COOKIE_KEY in cookies:
            del cookies[AUTH_COOKIE_KEY]
        cookies.save()
    except Exception:
        pass
