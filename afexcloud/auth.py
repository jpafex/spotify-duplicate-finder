import streamlit as st

def require_login() -> None:
    """Simple session-only login gate (beta)."""
    if st.session_state.get("password_correct"):
        return

    st.title("🔐 AfexCloud Tool Login")

    with st.form("login_form"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if u == st.secrets["APP_USER"] and p == st.secrets["APP_PASS"]:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Invalid credentials.")

    st.stop()

def logout() -> None:
    st.session_state["password_correct"] = False
