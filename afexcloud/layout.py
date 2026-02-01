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

def _hide_pages_nav():
    """
    Hide Streamlit's built-in multipage navigation list in the sidebar.
    Streamlit generates that list automatically from /pages.
    This CSS hides it visually (best-effort).
    """
    st.markdown(
        """
        <style>
        /* Hide the built-in multipage navigation (Pages list) */
        section[data-testid="stSidebar"] nav { display: none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

def bootstrap_page():
    auth_manager = None
    try:
        auth_manager = get_auth_manager()
        handle_spotify_callback(auth_manager)
    except Exception as e:
        st.session_state["_spotify_boot_error"] = str(e)

    if not is_logged_in():
        _hide_pages_nav()

    render_sidebar(auth_manager)

    if not is_logged_in():
        ok = show_login_form()
        if not ok:
            st.stop()



def render_sidebar(auth_manager=None):
    if auth_manager is None:
        auth_manager = get_auth_manager()

    token_info = get_valid_token_info(auth_manager)

    if "global_proj" not in st.session_state:
        st.session_state["global_proj"] = ""

    with st.sidebar:
        st.write("")  # small spacer
        st.subheader("☁️ AfexCloud")
        st.caption(f"v{APP_VERSION}")
        st.write("---")

        # Project field
        st.session_state["global_proj"] = st.text_input(
            "📁 Global Project:",
            value=st.session_state["global_proj"],
        )
        if st.button("🔄 Reset Project"):
            st.session_state["global_proj"] = ""
            st.rerun()

        st.write("---")

        # Spotify status + connect/disconnect
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

        # Logout
        if st.button("🚪 Log Out"):
            logout()
            auth_manager.cache_handler.delete_cached_token()
            st.rerun()

    # Handy “globals” pages can use
    st.session_state["_spotify_token_info"] = token_info
    st.session_state["_safe_proj"] = re.sub(
        r"[^a-zA-Z0-9_]", "_", st.session_state["global_proj"]
    )
