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
    """
    Call at the TOP of every page (and app.py).

    Beta flow:
    1) Process Spotify callback first (so token exchange works even if login is shown)
    2) Render sidebar (so Connect Spotify button always exists)
    3) If not logged in: hide the Pages list, show login form, stop page content
    """
    # Best-effort: try to process Spotify callback, but don't crash the app if it fails
    auth_manager = None
    spotify_boot_error = None
    try:
        auth_manager = get_auth_manager()
        handle_spotify_callback(auth_manager)
    except Exception as e:
        spotify_boot_error = str(e)

    # If not logged in, hide the Streamlit Pages nav BEFORE rendering sidebar/login
    if not is_logged_in():
        _hide_pages_nav()

    # Always render sidebar (even pre-login) so user can see Spotify status/connect
    render_sidebar(auth_manager=auth_manager, spotify_boot_error=spotify_boot_error)

    # Gate page content
    if not is_logged_in():
        ok = show_login_form()
        if not ok:
            st.stop()

def render_sidebar(auth_manager=None, spotify_boot_error: str | None = None):
    token_info = None

    # If auth_manager exists, attempt to validate token, but do not crash on errors
    if auth_manager is not None:
        try:
            token_info = get_valid_token_info(auth_manager)
        except Exception as e:
            spotify_boot_error = spotify_boot_error or str(e)
            token_info = None

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
        if spotify_boot_error:
            st.warning("Spotify auth is unavailable right now.")
            st.caption(f"Details: {spotify_boot_error}")
        else:
            if token_info:
                st.success("🟢 Spotify: Connected")
                if st.button("🔌 Disconnect Spotify"):
                    if auth_manager is not None:
                        auth_manager.cache_handler.delete_cached_token()
                    st.rerun()
            else:
                st.error("🔴 Spotify: Not Connected")
                if auth_manager is not None:
                    auth_url = get_connect_url(auth_manager)
                    try:
                        st.link_button("Connect Spotify", auth_url)
                    except Exception:
                        st.markdown(f"[Connect Spotify]({auth_url})")
                else:
                    st.caption("Spotify connection is not initialized.")

        st.write("---")

        # Logout
        if st.button("🚪 Log Out"):
            logout()
            if auth_manager is not None:
                try:
                    auth_manager.cache_handler.delete_cached_token()
                except Exception:
                    pass
            st.rerun()

    # Handy “globals” pages can use
    st.session_state["_spotify_token_info"] = token_info
    st.session_state["_safe_proj"] = re.sub(
        r"[^a-zA-Z0-9_]", "_", st.session_state["global_proj"]
    )
