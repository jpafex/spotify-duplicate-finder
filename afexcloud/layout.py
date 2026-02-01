import re
import streamlit as st

from .auth import require_login, logout
from .config import APP_VERSION
from .spotify_auth import get_auth_manager, handle_spotify_callback, get_valid_token_info, get_connect_url

def bootstrap_page():
    """
    Beta order:
    1) Process Spotify callback first (so token exchange works even if login is shown later)
    2) Then require AfexCloud login
    3) Render sidebar
    """
    auth_manager = get_auth_manager()
    handle_spotify_callback(auth_manager)

    require_login()
    render_sidebar(auth_manager)

def render_sidebar(auth_manager=None):
    if auth_manager is None:
        auth_manager = get_auth_manager()

    token_info = get_valid_token_info(auth_manager)

    if "global_proj" not in st.session_state:
        st.session_state["global_proj"] = ""

    with st.sidebar:
        st.title("☁️ AfexCloud")
        st.caption(f"v{APP_VERSION}")
        st.write("---")

        st.session_state["global_proj"] = st.text_input("📁 Global Project:", value=st.session_state["global_proj"])
        if st.button("🔄 Reset Project"):
            st.session_state["global_proj"] = ""
            st.rerun()

        st.write("---")

        if token_info:
            st.success("🟢 Spotify: Connected")
            if st.button("🔌 Disconnect Spotify"):
                auth_manager.cache_handler.delete_cached_token()
                st.rerun()
        else:
            st.error("🔴 Spotify: Not Connected")
            auth_url = get_connect_url(auth_manager)
            try:
                st.link_button("Connect Spotify", auth_url)
            except Exception:
                st.markdown(f"[Connect Spotify]({auth_url})")

        st.write("---")
        if st.button("🚪 Log Out"):
            logout()
            auth_manager.cache_handler.delete_cached_token()
            st.rerun()

    st.session_state["_spotify_token_info"] = token_info
    st.session_state["_safe_proj"] = re.sub(r"[^a-zA-Z0-9_]", "_", st.session_state["global_proj"])
