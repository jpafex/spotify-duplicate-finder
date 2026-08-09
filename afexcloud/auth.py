import streamlit as st

def is_logged_in() -> bool:
    return bool(st.session_state.get("password_correct"))

def show_login_form() -> bool:
    """Renders login UI and returns True once authenticated."""
    if is_logged_in():
        return True

    # --- Restore input field borders (global fix) ---
    st.markdown("""
    <style>
    div[data-testid="stTextInput"] input {
        border: 1px solid #cccccc !important;
        border-radius: 4px !important;
        padding: 0.5rem !important;
        background-color: white !important;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #ff4b4b !important;
        box-shadow: 0 0 0 0.2rem rgba(255, 75, 75, 0.25) !important;
    }
    </style>
    """, unsafe_allow_html=True)

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
