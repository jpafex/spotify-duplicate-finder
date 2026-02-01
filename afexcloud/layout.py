import re
import streamlit as st

# NOTE: keep imports minimal at module import-time
from .auth import require_login, logout

def bootstrap_page():
    """
    Call at the top of every page.
    Keeps the app bootable even if Spotify modules have a problem.
    """
    require_login()
    render_sidebar()

def render_sidebar():
    # Import these lazily so one failure doesn't crash the whole app at import-time
    try:
        from .config import APP_VERSION
    except Exception:
        APP_VERSION = "unknown"

    token_info = None
    auth_manager = None
    spotify_error = None

    try:
        from .spotify_auth import (
            get_auth_manager,
            handle_spotify_callback,
            get_valid_token_info,
            get_connect_url,
        )

        auth_manager = get_auth_manager()

        # If Spotify redirected back with a code, process it here
        handle_spotify_callback(auth_manager)

        token_info = get_valid_token_info(auth_manager)

    except Exception as e:
        spotify_error = e

    if "global_proj" not in st.session_state:
        st.session_state["global_proj"] = ""

    with st.sidebar:
        st.title("☁️ AfexCloud")
        st.caption(f"v{APP_VERSION}")
        st.write("---")

        st.session_state["global_proj"] = st.text_input(
            "📁 Global Project:",
            value=st.session_state["global_proj"]
        )
        if st.button("🔄 Reset Project"):
            st.session_state["global_proj"] = ""
            st.rerun()

        st.write("---")

        # Spotify status section
        if spotify_error is not None:
            st.warning("Spotify module didn’t load (app will still run).")
            st.caption(f"Details: {spotify_error}")
        else:
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
            if auth_manager is not None:
                auth_manager.cache_handler.delete_cached_token()
            st.rerun()

    # Expose these to pages if they want them
    st.session_state["_spotify_token_info"] = token_info
    st.session_state["_safe_proj"] = re.sub(r"[^a-zA-Z0-9_]", "_", st.session_state["global_proj"])
