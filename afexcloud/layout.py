import re
import streamlit as st
import os

from .config import APP_VERSION
from .auth import is_logged_in, show_login_form, logout
from .spotify_auth import (
    get_auth_manager,
    handle_spotify_callback,
    get_valid_token_info,
    get_connect_url,
)

def _hide_pages_nav():
    """Hides the default Streamlit sidebar menu to use our custom one."""
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] nav { display: none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

def bootstrap_page():
    """The central engine for AfexCloud branding, auth, and navigation."""
    _hide_pages_nav()
    
    auth_manager = None
    spotify_boot_error = None
    try:
        auth_manager = get_auth_manager()
        handle_spotify_callback(auth_manager)
    except Exception as e:
        spotify_boot_error = str(e)

    token_info = get_valid_token_info(auth_manager)

    with st.sidebar:
        st.title("☁️ AfexCloud")
        st.write("---")

        # 1. Project Management
        if "global_proj" not in st.session_state:
            st.session_state["global_proj"] = ""
        
        st.session_state["global_proj"] = st.text_input(
            "📁 Global Project:", value=st.session_state["global_proj"]
        )
        
        # Unique key added to prevent DuplicateElementId error
        if st.button("🔄 Reset Project Name", key="reset_proj_btn"):
            st.session_state["global_proj"] = ""
            st.rerun()
            
        st.write("---")

        # 2. Spotify Status
        if spotify_boot_error:
            st.warning("Spotify connection error.")
            st.caption(f"Details: {spotify_boot_error}")
        else:
            if token_info:
                st.success("🟢 Spotify: Connected")
            else:
                st.error("🔴 Spotify: Not Connected")
                auth_url = get_connect_url(auth_manager)
                st.markdown(f"[Connect Spotify]({auth_url})")

        st.write("---")

        # 3. Custom Navigation
        st.write("**Select a Tool:**")
        st.page_link("app.py", label="🏠 Home")
        
        # Tool Links - using a try/except to handle missing files gracefully
        try:
            st.page_link("pages/duplicate_finder.py", label="🔍 Duplicate Finder")
            st.page_link("pages/song_lister.py", label="📋 Song Lister")
            st.page_link("pages/batch_manager.py", label="📦 Batch Manager")
            st.page_link("pages/playlist_deleter.py", label="🗑️ Playlist Deleter")
            st.page_link("pages/sidecar_scraper.py", label="🕵️ Sidecar Scraper")
        except Exception:
            st.caption("⚠️ Note: Some tool files are not yet in the /pages folder.")

        # 4. Troubleshooting Section
        st.write("---")
        st.caption("🔧 Troubleshooting")
        if st.button("🔄 Force Clear Spotify Cache", key="force_cache_btn"):
            if os.path.exists(".cache-token"):
                os.remove(".cache-token")
                st.success("Cache cleared! Please reconnect.")
            else:
                st.info("No cache file found on server.")
            st.session_state.clear()
            st.rerun()

        # 5. Logout & Footer
        st.write("---")
        if st.button("🚪 Log Out", key="logout_btn"):
            logout()
            st.rerun()
        
        proj_display = st.session_state['global_proj'] if st.session_state['global_proj'] else 'Default'
        st.caption(f"AfexCloud v{APP_VERSION} | Project: {proj_display}")

    # Secure the page
    if not is_logged_in():
        show_login_form()
        st.stop()

    return auth_manager, token_info
