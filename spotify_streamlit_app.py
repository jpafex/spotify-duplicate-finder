import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import pandas as pd
from math import ceil
import io
import zipfileimport streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import pandas as pd
from math import ceil
import io
import zipfile
import time # Added for the 'report' timing effect

# Page config
st.set_page_config(page_title="AfexCloud Dashboard", page_icon="☁️", layout="wide")

# --- [LOGIN & AUTH SECTIONS REMAIN THE SAME - KEPT SECURE FOR JPAFEX] ---
# ... (All your working Login/Auth code stays exactly as is) ...

if "password_correct" in st.session_state and st.session_state["password_correct"]:
    # (Assuming existing logic for sp_read and auth_manager is here)

    # --- 5. BATCH MANAGER (Updated with Success Report) ---
    if st.session_state.get('choice') == "📦 Batch Manager":
        st.title("📦 Batch Management Tool")
        tab1, tab2 = st.tabs(["Step 1: Create CSV Batches", "Step 2: Upload to Spotify"])

        with tab1:
            st.subheader("1. Split Playlist into Batches")
            # [Step 1 Logic Stays Here]

        with tab2:
            st.subheader("2. Upload Batches to Spotify")
            
            # (Assuming existing token check logic is here)
            token_info = auth_manager.validate_token(auth_manager.cache_handler.get_cached_token())
            
            if token_info:
                st.success("✅ Spotify Connected")
                uploaded_files = st.file_uploader("Upload Batch CSVs", accept_multiple_files=True, type="csv")
                
                if st.button("🚀 Create Spotify Playlists", type="primary"):
                    if uploaded_files:
                        sp_write = spotipy.Spotify(auth_manager=auth_manager)
                        user_id = sp_write.current_user()['id']
                        
                        # --- SUCCESS REPORT DATA ---
                        total_songs_processed = 0
                        playlists_created = []
                        start_time = time.time()

                        with st.status("Processing Batches...", expanded=True) as status:
                            for f in uploaded_files:
                                try:
                                    df = pd.read_csv(f)
                                    if 'Spotify - id' in df.columns:
                                        song_count = len(df)
                                        p_name = f"Batch: {f.name}"
                                        p = sp_write.user_playlist_create(user=user_id, name=p_name, public=False)
                                        uris = [f"spotify:track:{tid}" for tid in df['Spotify - id'].tolist()]
                                        sp_write.playlist_add_items(p['id'], uris)
                                        
                                        # Track data for report
                                        total_songs_processed += song_count
                                        playlists_created.append({"File": f.name, "Songs": song_count, "Status": "✅ Success"})
                                        st.write(f"Created: {p_name} ({song_count} tracks)")
                                except Exception as e:
                                    playlists_created.append({"File": f.name, "Songs": 0, "Status": f"❌ Error: {e}"})
                            
                            status.update(label="Upload Complete!", state="complete", expanded=False)

                        # --- THE SUCCESS REPORT (The Cherry on Top) ---
                        st.write("---")
                        st.balloons()
                        st.header("📊 Batch Upload Success Report")
                        
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Total Playlists Created", len(playlists_created))
                        col2.metric("Total Tracks Uploaded", total_songs_processed)
                        col3.metric("Processing Time", f"{round(time.time() - start_time, 2)}s")

                        st.write("### 📜 Detailed Log")
                        report_df = pd.DataFrame(playlists_created)
                        st.table(report_df) # Using table for a clean, non-interactive print view
                        
                        # Manager Export Option
                        st.download_button(
                            "📥 Download Success Report (CSV)", 
                            report_df.to_csv(index=False).encode('utf-8'), 
                            "batch_upload_report.csv", 
                            "text/csv"
                        )
                    else:
                        st.error("Please upload files first.")

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

    auth_manager = get_auth_manager()

    # --- 3. AUTO-CAPTURE HANDSHAKE ---
    # This tries to catch the code from the URL and "exchange" it for a token
    if "code" in st.query_params:
        try:
            code = st.query_params.get("code")
            auth_manager.get_access_token(code, as_dict=False)
            # Clear the URL parameters so we don't try to use the code again
            st.query_params.clear()
            st.success("✅ Spotify Connection Verified!")
        except Exception as e:
            # If the code is expired/invalid, we just clear it and let the user try again
            st.query_params.clear()
            st.warning("Previous connection attempt expired. Please try authorizing again.")

    # --- 4. SIDEBAR ---
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
            # [Existing Batch/ZIP logic stays here]
            st.write("Step 1 Ready.")

        with tab2:
            st.subheader("2. Upload Batches to Spotify")
            
            token_info = auth_manager.validate_token(auth_manager.cache_handler.get_cached_token())
            
            if not token_info:
                auth_url = auth_manager.get_authorize_url()
                st.warning("🔑 Spotify Authorization Required")
                st.markdown(f"[**Click Here to Authorize AfexCloud on Spotify**]({auth_url})")
                
                manual_url = st.text_input("If it didn't auto-connect, paste the NEW URL from your browser here:")
                if st.button("Complete Connection"):
                    if manual_url:
                        try:
                            code = auth_manager.parse_response_code(manual_url)
                            auth_manager.get_access_token(code, as_dict=False)
                            st.success("✅ Connected!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Handshake failed: {e}. Try clicking the link above again for a fresh code.")
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
    st.caption("AfexCloud Suite | Handshake Recovery Enabled")

