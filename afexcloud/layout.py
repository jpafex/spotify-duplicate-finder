import re
import streamlit as st

# Import your modular components
from .auth import is_logged_in, show_login_form, logout
from .spotify_auth import (
    get_auth_manager,
    handle_spotify_callback,
    get_valid_token_info,
    get_connect_url,
)

def _hide_default_nav():
    """Hides the default Streamlit pages list to restore custom styling."""
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] nav { display: none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

def bootstrap_page():
    """Restores the AfexCloud brand identity and sidebar logic."""
    _hide_default_nav()
    
    auth_manager = None
    try:
        auth_manager = get_auth_manager()
        handle_spotify_callback(auth_manager)
    except Exception as e:
        st.sidebar.error(f"Auth Error: {e}")

    token_info = get_valid_token_info(auth_manager)

    with st.sidebar:
        st.title("☁️ AfexCloud")
        st.write("---")

        # Global Project Persistence
        if "global_proj" not in st.session_state:
            st.session_state["global_proj"] = ""
        
        st.session_state["global_proj"] = st.text_input(
            "📁 Global Project:", value=st.session_state["global_proj"]
        )
        
        if st.button("🔄 Reset Project"):
            st.session_state["global_proj"] = ""
            st.rerun()
            
        st.write("---")

        # Spotify Connection Status
        if token_info:
            st.success("🟢 Spotify: Connected")
        else:
            st.error("🔴 Spotify: Not Connected")
            auth_url = get_connect_url(auth_manager)
            st.markdown(f"[Connect Spotify]({auth_url})")

        st.write("---")

        # Custom Navigation (Matches your new folder structure)
        st.write("**Select a Tool:**")
        st.page_link("app.py", label="🏠 Home")
        
        # Ensure these filenames exist in your /pages folder to avoid the error
        try:
            st.page_link("pages/duplicate_finder.py", label="🔍 Duplicate Finder")
            st.page_link("pages/song_lister.py", label="📋 Song Lister")
            st.page_link("pages/batch_manager.py", label="📦 Batch Manager")
            st.page_link("pages/playlist_deleter.py", label="🗑️ Playlist Deleter")
            st.page_link("pages/sidecar_scraper.py", label="🕵️ Sidecar Scraper")
        except Exception:
            st.caption("⚠️ Some tool pages are missing in /pages folder.")

      # ... your existing tool links are up here ...
        except Exception:
            st.caption("⚠️ Some tool pages are missing in /pages folder.")

        # --- PASTE THIS TROUBLESHOOTING BLOCK HERE ---
        st.write("---")
        st.caption("🔧 Troubleshooting")
        if st.button("🔄 Force Clear Spotify Cache"):
            import os
            cache_file = ".cache-token"
            if os.path.exists(cache_file):
                os.remove(cache_file)
                st.success("Cache cleared! Reconnect to update permissions.")
            else:
                st.info("No cache file found on server.")
            
            # Wipe session state to force a fresh 'Agree' handshake
            st.session_state.clear()
            st.rerun()
        # ---------------------------------------------

        st.write("---")
        if st.button("🚪 Log Out"):
            logout()
            st.rerun()  

        st.write("---")
        if st.button("🚪 Log Out"):
            logout()
            st.rerun()
        
        st.caption(f"AfexCloud | Project: {st.session_state['global_proj'] if st.session_state['global_proj'] else 'Default'}")

    # Secure the page
    if not is_logged_in():
        show_login_form()
        st.stop()

    return auth_manager, token_info
