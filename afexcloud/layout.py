import re
import streamlit as st

from .config import APP_VERSION
from .auth import require_login, logout
from .spotify_auth import get_auth_manager, handle_spotify_callback, get_valid_token_info, get_connect_url

def bootstrap_page():
    """
    Call at the top of every page:
    - enforce AfexCloud login
    - init + process Spotify callback
    - render common sidebar (project, spotify status, logout)
    """
    require_login()
    render_sidebar()

def render_sidebar():
    auth_manager = get_auth_manager()

    # If Spotify redirected back with a code, process it here
    handle_spotify_callback(auth_manager)

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
            # also remove spotify token on logout to keep behavior consistent
            auth_manager.cache_handler.delete_cached_token()
            st.rerun()

    # Expose these to pages if they want them
    st.session_state["_spotify_token_info"] = token_info
    st.session_state["_safe_proj"] = re.sub(r"[^a-zA-Z0-9_]", "_", st.session_state["global_proj"])

