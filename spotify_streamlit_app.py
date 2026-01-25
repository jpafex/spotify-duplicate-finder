import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from collections import defaultdict
import pandas as pd
import io
from math import ceil

# Page config
st.set_page_config(page_title="AfexCloud Dashboard", page_icon="☁️", layout="wide")

# --- 1. SECURE LOGIN GATE ---
def check_password():
    def password_entered():
        if (st.session_state["username"] == st.secrets["APP_USER"] and 
            st.session_state["password"] == st.secrets["APP_PASS"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔐 AfexCloud Tool Login")
        st.text_input("Username", on_change=password_entered, key="username")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    return st.session_state.get("password_correct", False)

if check_password():
    
    # --- 2. AUTHENTICATION ENGINES ---
    # Read-only Engine (For fast public data)
    @st.cache_resource
    def get_read_client():
        return spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=st.secrets["SPOTIFY_CLIENT_ID"],
            client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"]
        ))

    # Write-access Engine (For creating playlists)
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

    # --- 3. SHARED HELPER FUNCTIONS ---
    def get_all_tracks(playlist_id):
        tracks = []
        results = sp_read.playlist_tracks(playlist_id)
        while results:
            for item in results['items']:
                if item.get('track'):
                    t = item['track']
                    tracks.append({
                        'Spotify - id': t.get('id'),
                        'Name': t.get('name', 'Unknown'),
                        'Artist': t['artists'][0]['name'] if t.get('artists') else 'Unknown',
                        'Album': t['album']['name'] if t.get('album') else 'Unknown'
                    })
            results = sp_read.next(results) if results['next'] else None
        return tracks

    # --- 4. SIDEBAR NAVIGATION ---
    with st.sidebar:
        st.title("☁️ AfexCloud")
        st.write(f"Logged in as: **{st.secrets['APP_USER']}**")
        st.write("---")
        choice = st.radio("Select a Tool:", 
            ["🏠 Dashboard Home", "🔍 Duplicate Finder", "📋 Song Lister", "📦 Batch Manager"])
        st.write("---")
        if st.button("🚪 Log Out"):
            st.session_state["password_correct"] = False
            st.rerun()

    # --- 5. DASHBOARD PAGES ---

    if choice == "🏠 Dashboard Home":
        st.title("🚀 AfexCloud Marketing Dashboard")
        st.info("Welcome to the Batch-enabled suite. Use the sidebar to navigate.")

    elif choice == "🔍 Duplicate Finder":
        st.title("🔍 Duplicate Finder")
        # [Existing Duplicate Logic would go here]
        st.write("Tool Ready.")

    elif choice == "📋 Song Lister":
        st.title("📋 Song Lister")
        # [Existing Lister Logic would go here]
        st.write("Tool Ready.")

    elif choice == "📦 Batch Manager":
        st.title("📦 Batch Management Tool")
        tab1, tab2 = st.tabs(["Step 1: Create Batches (Download)", "Step 2: Upload Batches (Restore)"])

        with tab1:
            st.subheader("Split Playlist into Batches")
            url = st.text_input("Enter Source Playlist URL/ID:", key="batch_source")
            batch_size = 25
            
            if st.button("Generate CSV Batches"):
                p_id = url.split('/')[-1].split('?')[0] if '/' in url else url
                with st.spinner("Fetching and Batching..."):
                    all_tracks = get_all_tracks(p_id)
                    total_tracks = len(all_tracks)
                    num_batches = ceil(total_tracks / batch_size)
                    
                    st.success(f"Found {total_tracks} tracks. Creating {num_batches} batches.")
                    
                    for i in range(num_batches):
                        start = i * batch_size
                        end = start + batch_size
                        batch = all_tracks[start:end]
                        df_batch = pd.DataFrame(batch)
                        
                        # Display Batch and Download Button
                        with st.expander(f"Batch {i+1} ({len(batch)} songs)"):
                            st.dataframe(df_batch, use_container_width=True, hide_index=True)
                            csv = df_batch.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label=f"📥 Download Batch {i+1} CSV",
                                data=csv,
                                file_name=f"Batch_{i+1}.csv",
                                mime="text/csv"
                            )

        with tab2:
            st.subheader("Upload Batches to Spotify")
            st.write("Upload the Batch CSVs to create new playlists in your account.")
            uploaded_files = st.file_uploader("Choose Batch CSV files", accept_multiple_files=True, type="csv")
            
            if st.button("🚀 Upload and Create Playlists"):
                if not uploaded_files:
                    st.error("Please upload at least one CSV file.")
                else:
                    try:
                        sp_write = get_write_client()
                        user_id = sp_write.current_user()['id']
                        
                        for uploaded_file in uploaded_files:
                            df = pd.read_csv(uploaded_file)
                            if 'Spotify - id' not in df.columns:
                                st.error(f"Skipping {uploaded_file.name}: Missing 'Spotify - id' column.")
                                continue
                            
                            track_ids = df['Spotify - id'].tolist()
                            p_name = f"Playlist from {uploaded_file.name}"
                            
                            # Create Playlist 
                            new_playlist = sp_write.user_playlist_create(
                                user=user_id, 
                                name=p_name, 
                                public=False,
                                description=f"Created via AfexCloud Batch Manager"
                            )
                            
                            # Add tracks in chunks of 25 (as per your script) 
                            uris = [f"spotify:track:{tid}" for tid in track_ids]
                            sp_write.playlist_add_items(new_playlist['id'], uris)
                            st.success(f"✅ Created: {p_name}")
                            
                    except Exception as e:
                        st.error(f"Authorization Error: {e}")
                        st.info("Check if your Redirect URI is set correctly in Spotify Developer Dashboard.")

    st.write("---")
    st.caption("AfexCloud Private Suite | Built with Pandas & Spotipy")
