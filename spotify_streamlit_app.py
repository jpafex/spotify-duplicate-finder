import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import pandas as pd
from math import ceil
import io
import zipfile

# Page config
st.set_page_config(page_title="AfexCloud Dashboard", page_icon="☁️", layout="wide")

# --- 1. LOGIN GATE ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 AfexCloud Tool Login")
        with st.form("login_form"):
            user_input = st.text_input("Username")
            pass_input = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            if submit:
                if user_input == st.secrets["APP_USER"] and pass_input == st.secrets["APP_PASS"]:
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
        return False
    return st.session_state.get("password_correct", True)

if check_password():
    
    # --- 2. AUTHENTICATION (Interactive Flow) ---
    @st.cache_resource
    def get_read_client():
        return spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=st.secrets["SPOTIFY_CLIENT_ID"],
            client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"]
        ))

    # This function now handles the "One-Time Handshake" on the screen
    def get_write_client():
        scope = "playlist-modify-public playlist-modify-private"
        auth_manager = SpotifyOAuth(
            client_id=st.secrets["SPOTIFY_CLIENT_ID"],
            client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"],
            redirect_uri=st.secrets["SPOTIFY_REDIRECT_URI"],
            scope=scope,
            open_browser=False,
            cache_path=".cache-token" # Remembers you after the first time
        )
        
        # Check if we already have a token
        token_info = auth_manager.validate_token(auth_manager.cache_handler.get_cached_token())
        
        if not token_info:
            auth_url = auth_manager.get_authorize_url()
            st.warning("🔑 Spotify Authorization Required")
            st.write("To create playlists, we need a one-time connection to your account:")
            st.markdown(f"[1. Click here to log in and authorize Spotify]({auth_url})")
            st.write("2. After clicking 'Agree', you will be sent to a blank page or AfexCloud.")
            response_url = st.text_input("3. Paste the ENTIRE URL from your browser's address bar here:")
            
            if response_url:
                code = auth_manager.parse_response_code(response_url)
                auth_manager.get_access_token(code, as_dict=False)
                st.success("✅ Authorization Successful! Please click 'Create Spotify Playlists' again.")
                st.rerun()
            return None # Stop here until they paste the URL
            
        return spotipy.Spotify(auth_manager=auth_manager)

    sp_read = get_read_client()

    # --- 3. SIDEBAR ---
    with st.sidebar:
        st.title("☁️ AfexCloud")
        choice = st.radio("Select a Tool:", ["🏠 Home", "🔍 Duplicate Finder", "📋 Song Lister", "📦 Batch Manager"])
        st.write("---")
        if st.button("🚪 Log Out"):
            st.session_state["password_correct"] = False
            st.rerun()

    # --- 4. BATCH MANAGER (Updated Upload Logic) ---
    if choice == "📦 Batch Manager":
        st.title("📦 Batch Management Tool")
        tab1, tab2 = st.tabs(["Step 1: Create CSV Batches", "Step 2: Upload to Spotify"])

        with tab1:
            # [Step 1 logic stays the same for splitting/downloading ZIP]
            st.write("Step 1 Ready.")

        with tab2:
            st.subheader("2. Upload Batches to Create New Playlists")
            uploaded_files = st.file_uploader("Upload Batch CSVs", accept_multiple_files=True, type="csv")
            
            if st.button("🚀 Create Spotify Playlists"):
                sp_write = get_write_client() # This now triggers the interactive box if needed
                
                if sp_write:
                    try:
                        user_id = sp_write.current_user()['id']
                        for f in uploaded_files:
                            df = pd.read_csv(f)
                            if 'Spotify - id' in df.columns:
                                p_name = f"Batch: {f.name}"
                                p = sp_write.user_playlist_create(user=user_id, name=p_name, public=False)
                                uris = [f"spotify:track:{tid}" for tid in df['Spotify - id'].tolist()]
                                sp_write.playlist_add_items(p['id'], uris)
                                st.success(f"✅ Playlist Created: {f.name}")
                    except Exception as e:
                        st.error(f"Error: {e}")

    st.write("---")
    st.caption("AfexCloud Suite | Interactive Auth Enabled")
