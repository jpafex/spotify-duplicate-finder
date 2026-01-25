import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from collections import defaultdict
import pandas as pd
from math import ceil

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

    def get_write_client():
        scope = "playlist-modify-public playlist-modify-private"
        return spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=st.secrets["SPOTIFY_CLIENT_ID"],
            client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"],
            redirect_uri=st.secrets["SPOTIFY_REDIRECT_URI"],
            scope=scope,
            open_browser=False
        ))

    sp_read = get_read_client()

    # --- 3. UPDATED HELPER FUNCTIONS (Preserving Global Position) ---
    def get_all_tracks_with_pos(playlist_id):
        """Fetches tracks and assigns their original global position number."""
        tracks = []
        try:
            results = sp_read.playlist_tracks(playlist_id)
            current_pos = 1
            while results:
                for item in results['items']:
                    if item.get('track'):
                        t = item['track']
                        tracks.append({
                            'Original Pos': current_pos, # Fixed Global Counter
                            'Spotify - id': t.get('id'),
                            'Name': t.get('name', 'Unknown'),
                            'Artist': t['artists'][0]['name'] if t.get('artists') else 'Unknown',
                            'Album': t['album']['name'] if t.get('album') else 'Unknown'
                        })
                        current_pos += 1
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
        st.info("Now tracking Global Positions in all batches.")

    elif choice == "📦 Batch Manager":
        st.title("📦 Batch Management Tool")
        tab1, tab2 = st.tabs(["Step 1: Create CSV Batches", "Step 2: Upload to Spotify"])

        with tab1:
            st.subheader("1. Split Playlist into Batches of 25")
            url = st.text_input("Source Playlist URL/ID:", key="batch_source")
            if st.button("Generate Batches"):
                p_id = url.split('/')[-1].split('?')[0] if '/' in url else url
                all_tracks = get_all_tracks_with_pos(p_id)
                num_batches = ceil(len(all_tracks) / 25)
                
                for i in range(num_batches):
                    batch = all_tracks[i*25 : (i+1)*25]
                    df_batch = pd.DataFrame(batch)
                    
                    # Ensure columns are in the correct order for the team
                    df_batch = df_batch[['Original Pos', 'Name', 'Artist', 'Album', 'Spotify - id']]
                    
                    range_label = f"{batch[0]['Original Pos']} to {batch[-1]['Original Pos']}"
                    with st.expander(f"Batch {i+1} (Tracks {range_label})"):
                        st.dataframe(df_batch, use_container_width=True, hide_index=True)
                        csv = df_batch.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label=f"📥 Download Batch {i+1} CSV",
                            data=csv,
                            file_name=f"Batch_{i+1}_Tracks_{range_label}.csv",
                            mime="text/csv"
                        )

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
                            # Using the file name as the playlist name for clarity
                            p = sp_write.user_playlist_create(user=user_id, name=f"Batch: {f.name}", public=False)
                            uris = [f"spotify:track:{tid}" for tid in df['Spotify - id'].tolist()]
                            sp_write.playlist_add_items(p['id'], uris)
                            st.success(f"Playlist Created: {f.name}")
                except Exception as e:
                    st.error(f"Auth Error: {e}")

    # [Note: Duplicate Finder and Song Lister sections remain in the full script as previously built]
    st.write("---")
    st.caption("AfexCloud Suite | Global Position Tracking Enabled")
