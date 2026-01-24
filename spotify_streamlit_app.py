import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from collections import defaultdict
import pandas as pd

# Page config - "Wide" mode looks best for the data tables
st.set_page_config(page_title="Spotify Duplicate Finder", page_icon="🎵", layout="wide")

# --- LOGIN LOGIC (Gated via Streamlit Secrets) ---
def check_password():
    """Returns True if the user had the correct password."""
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if (
            st.session_state["username"] == st.secrets["APP_USER"]
            and st.session_state["password"] == st.secrets["APP_PASS"]
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Security: don't store password in session
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Initial state: Show the login screen overlay
        st.title("🔐 AfexCloud Spotify Tool Login")
        st.text_input("Username", on_change=password_entered, key="username")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # Wrong credentials entered
        st.title("🔐 AfexCloud Spotify Tool Login")
        st.text_input("Username", on_change=password_entered, key="username")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("Invalid Username or Password.")
        return False
    else:
        # User is authenticated
        return True

# Trigger the lock
if check_password():
    
    # Spotify credentials retrieval
    try:
        CLIENT_ID = st.secrets["SPOTIFY_CLIENT_ID"]
        CLIENT_SECRET = st.secrets["SPOTIFY_CLIENT_SECRET"]
    except KeyError:
        st.error("Critical Error: Missing Spotify API credentials in Secrets.")
        st.stop()

    # Initialize Spotify client (cached for performance)
    @st.cache_resource
    def get_spotify_client():
        auth_manager = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
        return spotipy.Spotify(auth_manager=auth_manager)

    sp = get_spotify_client()

    # --- HELPER LOGIC ---
    def get_playlist_tracks(playlist_id):
        tracks = []
        try:
            results = sp.playlist_tracks(playlist_id)
            while results:
                for item in results['items']:
                    if item.get('track'):
                        track = item['track']
                        tracks.append({
                            'id': track.get('id'),
                            'name': track.get('name', 'Unknown'),
                            'artist': track['artists'][0]['name'] if track.get('artists') else 'Unknown',
                            'album': track['album']['name'] if track.get('album') else 'Unknown',
                        })
                results = sp.next(results) if results['next'] else None
        except Exception as e:
            st.error(f"Error connecting to Spotify API: {e}")
            return []
        return tracks

    def find_duplicates(tracks):
        by_id = defaultdict(list)
        by_name_artist = defaultdict(list)
        for i, track in enumerate(tracks):
            pos = i + 1
            if track['id']:
                by_id[track['id']].append({**track, 'position': pos})
            key = f"{track['name'].lower()}::{track['artist'].lower()}"
            by_name_artist[key].append({**track, 'position': pos})
        
        exact = {k: v for k, v in by_id.items() if len(v) > 1}
        similar = {k: v for k, v in by_name_artist.items() if len(v) > 1}
        return exact, similar

    # --- MAIN APP INTERFACE ---
    st.title("🎵 Spotify Duplicate Finder")
    
    with st.sidebar:
        st.header("App Controls")
        if st.button("🔄 Refresh / Clear App"):
            st.cache_resource.clear()
            if 'playlist_input' in st.session_state:
                st.session_state['playlist_input'] = ""
            st.rerun()
        
        st.write("---")
        if st.button("🚪 Log Out"):
            st.session_state["password_correct"] = False
            st.rerun()

    playlist_url = st.text_input(
        "Enter Spotify Playlist URL or ID:", 
        placeholder="e.g., https://open.spotify.com/playlist/...",
        key="playlist_input"
    )

    if st.button("🔍 Run Analysis", type="primary"):
        if not playlist_url:
            st.error("Please provide a playlist link first.")
        else:
            # Robust extraction handles URLs or raw IDs
            playlist_id = playlist_url.split('/')[-1].split('?')[0] if '/' in playlist_url else playlist_url
            
            with st.spinner("Scanning playlist for duplicates..."):
                tracks = get_playlist_tracks(playlist_id)
                if not tracks:
                    st.warning("No tracks found. Please verify the playlist is public.")
                else:
                    exact, similar = find_duplicates(tracks)
                    
                    # Consolidate all duplicates for the spreadsheet view
                    all_dupes = []
                    for tid, dupes in exact.items():
                        for d in dupes:
                            all_dupes.append({**d, 'Type': 'Exact Match'})
                    for key, dupes in similar.items():
                        for d in dupes:
                            if not any(x['id'] == d['id'] and x['position'] == d['position'] for x in all_dupes):
                                all_dupes.append({**d, 'Type': 'Similar (Name/Artist)'})

                    if not all_dupes:
                        st.balloons()
                        st.success("🎉 Your playlist is 100% clean!")
                    else:
                        # 1. Dashboard Metrics
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Total Tracks", len(tracks))
                        c2.metric("Exact Duplicates", len(exact))
                        c3.metric("Similar Tracks", len(similar))

                        # 2. Spreadsheet Preview
                        df = pd.DataFrame(all_dupes)
                        df = df[['position', 'name', 'artist', 'album', 'Type', 'id']]
                        df.columns = ['Pos', 'Track Name', 'Artist', 'Album', 'Match Type', 'Spotify ID']
                        st.write("### 📋 Duplicate Data Grid")
                        st.dataframe(df, use_container_width=True, hide_index=True)

                        # 3. Multi-Format Export Suite
                        st.write("### 💾 Export Results")
                        e_col1, e_col2, e_col3 = st.columns(3)
                        
                        # Generate export formats
                        csv_file = df.to_csv(index=False).encode('utf-8')
                        txt_file = "AFEXCLOUD SPOTIFY REPORT\n" + "="*25 + "\n"
                        for _, r in df.iterrows():
                            txt_file += f"Pos: {r['Pos']} | {r['Track Name']} - {r['Artist']} ({r['Album']})\n"

                        with e_col1:
                            st.download_button("📊 Download CSV", csv_file, "spotify_dupes.csv", "text/csv", use_container_width=True)
                        with e_col2:
                            st.download_button("📥 Download TXT", txt_file, "spotify_dupes.txt", "text/plain", use_container_width=True)
                        with e_col3:
                            with st.popover("📋 Copy to Clipboard", use_container_width=True):
                                st.code(txt_file, language="text")

    st.write("---")
    st.caption("Secured for jpafex | Built with Streamlit, Spotipy & Pandas")
