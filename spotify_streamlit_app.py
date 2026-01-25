import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from collections import defaultdict
import pandas as pd
from math import ceil

# Page config
st.set_page_config(page_title="AfexCloud Dashboard", page_icon="☁️", layout="wide")

# --- 1. SECURE LOGIN GATE (Form-Based to prevent blank screen) ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 AfexCloud Tool Login")
        # Using a form makes the login much more stable
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
    return st.session_state.get("password_correct", False)

if check_password():
    
    # --- 2. AUTHENTICATION ENGINES ---
    @st.cache_resource
    def get_read_client():
        """Read-only access for searching and listing (no login required)"""
        return spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=st.secrets["SPOTIFY_CLIENT_ID"],
            client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"]
        ))

    def get_write_client():
        """Write-access for creating playlists (requires user authentication)"""
        scope = "playlist-modify-public playlist-modify-private"
        return spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=st.secrets["SPOTIFY_CLIENT_ID"],
            client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"],
            redirect_uri=st.secrets["SPOTIFY_REDIRECT_URI"],
            scope=scope,
            open_browser=False
        ))

    sp_read = get_read_client()

    # --- 3. HELPER FUNCTIONS ---
    def get_all_tracks(playlist_id):
        """Standardizes track fetching for all tools """
        tracks = []
        try:
            results = sp_read.playlist_tracks(playlist_id)
            while results:
                for item in results['items']:
                    if item.get('track'):
                        t = item['track']
                        tracks.append({
                            'Spotify - id': t.get('id'), # Matching Batch script 
                            'Name': t.get('name', 'Unknown'),
                            'Artist': t['artists'][0]['name'] if t.get('artists') else 'Unknown',
                            'Album': t['album']['name'] if t.get('album') else 'Unknown'
                        })
                results = sp_read.next(results) if results['next'] else None
        except Exception as e:
            st.error(f"Spotify API Error: {e}")
            return []
        return tracks

    # --- 4. SIDEBAR NAVIGATION ---
    with st.sidebar:
        st.title("☁️ AfexCloud")
        choice = st.radio("Select a Tool:", 
            ["🏠 Home", "🔍 Duplicate Finder", "📋 Song Lister", "📦 Batch Manager"])
        st.write("---")
        if st.button("🚪 Log Out"):
            st.session_state["password_correct"] = False
            st.rerun()

    # --- 5. DASHBOARD PAGES ---

    if choice == "🏠 Home":
        st.title("🚀 AfexCloud Marketing Dashboard")
        st.info("Welcome to the Batch-enabled suite. Use the sidebar to navigate.")

    elif choice == "🔍 Duplicate Finder":
        st.title("🔍 Spotify Duplicate Finder")
        url = st.text_input("Enter Playlist URL:", key="dup_input")
        if st.button("Run Duplicate Scan"):
            tracks = get_all_tracks(url.split('/')[-1].split('?')[0] if '/' in url else url)
            if tracks:
                # [Simplified dupe logic for brevity - keeping your exact functionality cite: 1]
                by_id = defaultdict(list)
                for i, t in enumerate(tracks): by_id[t['Spotify - id']].append({**t, 'pos': i+1})
                dupes = {k: v for k, v in by_id.items() if len(v) > 1}
                st.write(f"Found {len(dupes)} duplicates.")
                if dupes:
                    df = pd.DataFrame([d for group in dupes.values() for d in group])
                    st.dataframe(df)

    elif choice == "📋 Song Lister":
        st.title("📋 Playlist Song Lister")
        url = st.text_input("Enter Playlist URL:", key="list_input")
        if st.button("Generate Inventory"):
            tracks = get_all_tracks(url.split('/')[-1].split('?')[0] if '/' in url else url)
            if tracks:
                df = pd.DataFrame(tracks)
                st.dataframe(df, use_container_width=True)

    elif choice == "📦 Batch Manager":
        st.title("📦 Batch Management Tool")
        tab1, tab2 = st.tabs(["Step 1: Create CSV Batches", "Step 2: Upload to Spotify"])

        with tab1:
            st.subheader("1. Split Playlist into Batches of 25")
            url = st.text_input("Source Playlist URL/ID:", key="batch_source")
            if st.button("Generate Batches"):
                p_id = url.split('/')[-1].split('?')[0] if '/' in url else url
                all_tracks = get_all_tracks(p_id)
                num_batches = ceil(len(all_tracks) / 25)
                
                for i in range(num_batches):
                    batch = all_tracks[i*25 : (i+1)*25]
                    df_batch = pd.DataFrame(batch)
                    with st.expander(f"Batch {i+1} ({len(batch)} tracks)"):
                        st.dataframe(df_batch, use_container_width=True, hide_index=True)
                        st.download_button(f"📥 Download Batch {i+1} CSV", df_batch.to_csv(index=False).encode('utf-8'), f"Batch_{i+1}.csv", "text/csv")

        with tab2:
            st.subheader("2. Upload Batches to Create New Playlists")
            uploaded_files = st.file_uploader("Upload Batch CSVs", accept_multiple_files=True, type="csv")
            if st.button("🚀 Create Spotify Playlists"):
                try:
                    sp_write = get_write_client()
                    user_id = sp_write.current_user()['id']
                    for f in uploaded_files:
                        df = pd.read_csv(f)
                        if 'Spotify - id' in df.columns:
                            p = sp_write.user_playlist_create(user=user_id, name=f"Batch: {f.name}", public=False)
                            uris = [f"spotify:track:{tid}" for tid in df['Spotify - id'].tolist()]
                            sp_write.playlist_add_items(p['id'], uris)
                            st.success(f"Playlist Created: {f.name}")
                except Exception as e:
                    st.error(f"Auth Error: {e}")

    st.write("---")
    st.caption("AfexCloud Suite | Secured for jpafex")
