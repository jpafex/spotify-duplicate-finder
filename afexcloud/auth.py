import streamlit as st

def is_logged_in() -> bool:
    return bool(st.session_state.get("password_correct"))

def show_login_form() -> bool:
    """Renders login UI and returns True once authenticated."""
    if is_logged_in():
        return True

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

    return False

def logout() -> None:
    st.session_state["password_correct"] = False
