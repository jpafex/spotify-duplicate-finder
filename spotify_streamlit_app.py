import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import pandas as pd
from math import ceil
import io
import zipfile

# Page config
st.set_page_config(page_title="AfexCloud Dashboard", page_icon="☁️", layout="wide")

# --- 1. SECURE LOGIN GATE ---
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
    
    # --- 2. AUTHENTICATION ENGINES ---
    @st.cache_resource
    def get_read_client():
        return spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=st.secrets["SPOTIFY_CLIENT_ID"],
            client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"]
        ))

    def get_auth_manager():
        scope = "playlist-modify-public playlist-modify-private"
        return SpotifyOAuth(
            client_id=st.secrets["SPOTIFY_CLIENT_ID"],
            client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"],
            redirect_uri=st.secrets["SPOTIFY_REDIRECT_URI"],
            scope=scope,
            open_browser=False,
            cache_path=".cache-token"
        )

    sp_read = get_read_client()
    auth_manager = get_auth_manager()

    # --- 3. AUTO-CAPTURE LOGIC (The "Gold" Touch) ---
    # This checks the URL for that ?code= immediately after you log in
    if "code" in st.query_params and not auth_manager.validate_token(auth_manager.cache_handler.get_cached_token()):
        try:
            code = st.query_params.get("code")
            auth_manager.get_access_token(code, as_dict=False)
            st.success("✅ Spotify Connection Verified Automatically!")
        except Exception as e:
            st.error(f"Auto-auth failed: {e}")

    # --- 4. SIDEBAR NAVIGATION ---
    with st.sidebar:
        st.title("☁️ AfexCloud")
        choice = st.radio("Select a Tool:", ["🏠 Home", "🔍 Duplicate Finder", "📋 Song Lister", "📦 Batch Manager"])
        if st.button("🚪 Log Out"):
            st.session_state["password_correct"] = False
            st.rerun()

    # --- 5. BATCH MANAGER ---
    if choice == "📦 Batch Manager":
        st.title("📦 Batch Management Tool")
        tab1, tab2 = st.tabs(["Step 1: Create CSV Batches", "Step 2: Upload to Spotify"])

        with tab1:
            st.subheader("1. Split Playlist into Batches")
            st.write("Step 1 Logic Ready.") # Your existing code here

        with tab2:
            st.subheader("2. Upload Batches to Spotify")
            
            # --- AUTH CHECKBOX ---
            token_info = auth_manager.validate_token(auth_manager.cache_handler.get_cached_token())
            
            if not token_info:
                auth_url = auth_manager.get_authorize_url()
                st.warning("🔑 One-Time Spotify Authorization Required")
                st.markdown(f"[**Click Here to Authorize AfexCloud on Spotify**]({auth_url})")
                
                # The box is now permanently visible here if you aren't authorized
                manual_url = st.text_input("Paste the URL from your address bar here if it didn't auto-connect:")
                if st.button("Complete Connection"):
                    if manual_url:
                        code = auth_manager.parse_response_code(manual_url)
                        auth_manager.get_access_token(code, as_dict=False)
                        st.success("✅ Connected! You can now upload.")
                        st.rerun()
            else:
                st.success("✅ Spotify Connected")
                uploaded_files = st.file_uploader("Upload Batch CSVs", accept_multiple_files=True, type="csv")
                
                if st.button("🚀 Create Spotify Playlists"):
                    if uploaded_files:
                        sp_write = spotipy.Spotify(auth_manager=auth_manager)
                        user_id = sp_write.current_user()['id']
                        for f in uploaded_files:
                            df = pd.read_csv(f)
                            if 'Spotify - id' in df.columns:
                                p = sp_write.user_playlist_create(user=user_id, name=f"Batch: {f.name}", public=False)
                                uris = [f"spotify:track:{tid}" for tid in df['Spotify - id'].tolist()]
                                sp_write.playlist_add_items(p['id'], uris)
                                st.success(f"Playlist Created: {f.name}")
                    else:
                        st.error("Please upload files first.")

    st.write("---")
    st.caption("AfexCloud Suite | Auto-Auth & URL Capture Enabled")
