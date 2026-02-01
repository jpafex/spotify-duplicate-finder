import re
import streamlit as st

from .config import APP_VERSION
from .auth import is_logged_in, show_login_form, logout
from .spotify_auth import (
    get_auth_manager,
    handle_spotify_callback,
    get_valid_token_info,
    get_connect_url,
)

def bootstrap_page():
    """
    Beta flow:
    1) Always process Spotify callback first
    2) Always render sidebar (so Connect button exists)
    3) If not logged in, show login form and stop page content
    """
    auth_manager = get_auth_manager()
    handle_spotify_callback(auth_manager)

    # Sidebar always visible
    render_sidebar(auth_manager)

    # Gate page content
    if not is_logged_in():
        ok = show_login_form()
        if not ok:
            st.stop()

def render_sidebar(auth_manager):
    token_info = get_valid_token_info(auth_manager)

    if "global_proj" not in st.session_state:
        st.session_state["global_proj"] = ""

    with st.sidebar:
        st.title("☁️ AfexCloud")
        st.caption(f"v{APP_VERSION}")
        st.write("---")

        # Project field always visible
        st.session_state["global_proj"] = st.text_input(
            "📁 Global Project:",
            value=st.session_state["global_proj"]
        )
        if st.button("🔄 Reset Project"):
            st.session_state["global_proj"] = ""
            st.rerun()

        st.write("---")

        # Spotify section
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
