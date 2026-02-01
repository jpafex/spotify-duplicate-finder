import re
import streamlit as st
import unicodedata

# Note: Assumes you have an afexcloud/config.py with APP_VERSION = "3.1.0"
from .config import APP_VERSION
from .auth import is_logged_in, show_login_form, logout
from .spotify_auth import (
    get_auth_manager,
    handle_spotify_callback,
    get_valid_token_info,
    get_connect_url,
)

def _hide_pages_nav():
    """Hides Streamlit's default navigation to keep our custom look."""
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] nav { display: none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

def bootstrap_page():
    """The 'Look and Feel' Engine of AfexCloud."""
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
        # 1. Restoration of the Brand Header
        st.title("☁️ AfexCloud")
        st.write("---")

        # 2. Restoration of the Global Project Name Input
        if "global_proj" not in st.session_state:
            st.session_state["global_proj"] = ""
        
        st.session_state["global_proj"] = st.text_input(
            "📁 Global Project:", value=st.session_state["global_proj"]
        )
        
        if st.button("🔄 Reset Project"):
            st.session_state["global_proj"] = ""
            st.rerun()
            
        st.write("---")

        # 3. Restoration of Spotify Connection Status
        if spotify_boot_error:
            st.warning("Spotify auth is unavailable.")
        else:
            if token_info:
                st.success("🟢 Spotify: Connected")
            else:
                st.error("🔴 Spotify: Not Connected")
                auth_url = get_connect_url(auth_manager)
                st.markdown(f"[Connect Spotify]({auth_url})")

        st.write("---")

        # 4. Restoration of Tool Navigation (with Icons)
        # In a Multi-Page app, we use links to the actual filenames in your /pages folder
        st.write("**Select a Tool:**")
        st.page_link("app.py", label="🏠 Home")
        st.page_link("pages/duplicate_finder.py", label="🔍 Duplicate Finder")
        st.page_link("pages/song_lister.py", label="📋 Song Lister")
        st.page_link("pages/batch_manager.py", label="📦 Batch Manager")
        st.page_link("pages/playlist_deleter.py", label="🗑️ Playlist Deleter")
        st.page_link("pages/sidecar_scraper.py", label="🕵️ Sidecar Scraper")

        st.write("---")
        if st.button("🚪 Log Out"):
            logout()
            st.rerun()
        
        # 5. The Footer
        st.caption(f"AfexCloud v{APP_VERSION} | Project: {st.session_state['global_proj'] if st.session_state['global_proj'] else 'Default'}")

    # Secure the page
    if not is_logged_in():
        show_login_form()
        st.stop()

    return auth_manager, token_info
