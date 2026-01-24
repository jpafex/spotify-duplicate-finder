import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from collections import defaultdict
import pandas as pd
import io

# Page config
st.set_page_config(page_title="Spotify Duplicate Finder", page_icon="🎵", layout="wide")

# Title
st.title("🎵 Spotify Duplicate Finder")
st.write("Find duplicate songs in your Spotify playlists")

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("App Controls")
    
    def reset_app():
        # Clear cache and reset the input field
        st.cache_resource.clear()
        if 'playlist_input' in st.session_state:
            st.session_state['playlist_input'] = ""
        st.rerun()

    if st.button("🔄 Refresh / Clear All"):
        reset_app()
        
    st.info("Clears current results and resets the search box.")

# Spotify credentials
try:
    CLIENT_ID = st.secrets["SPOTIFY_CLIENT_ID"]
    CLIENT_SECRET = st.secrets["SPOTIFY_CLIENT_SECRET"]
except KeyError:
    st.error("Missing Spotify Credentials! Please add them to your Streamlit Secrets.")
    st.stop()

@st.cache_resource
def get_spotify_client():
    auth_manager = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    return spotipy.Spotify(auth_manager=auth_manager)

sp = get_spotify_client()

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
                        'name': track.get('name', 'Unknown Title'),
                        'artist': track['artists'][0]['name'] if track.get('artists') else 'Unknown Artist',
                        'album': track['album']['name'] if track.get('album') else 'Unknown Album',
                        'added_at': item.get('added_at')
                    })
            results = sp.next(results) if results['next'] else None
    except Exception as e:
        st.error(f"Failed to fetch playlist: {e}")
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

# --- MAIN UI ---
st.write("---")
playlist_url = st.text_input(
    "Enter Spotify Playlist URL or ID:", 
    placeholder="https://open.spotify.com/playlist/...",
    key="playlist_input"
)

if st.button("🔍 Find Duplicates", type="primary"):
    if not playlist_url:
        st.error("Please enter a playlist URL or ID")
    else:
        try:
            # Robust extraction logic
            if 'spotify.com' in playlist_url:
                playlist_id = playlist_url.split('/')[-1].split('?')[0]
            else:
                playlist_id = playlist_url
            
            with st.spinner("Analyzing playlist..."):
                tracks = get_playlist_tracks(playlist_id)
                
                if not tracks:
                    st.warning("No tracks found. Is the playlist public?")
                else:
                    exact, similar = find_duplicates(tracks)
                    st.success("✅ Analysis complete!")
                    
                    # 1. SUMMARY METRICS
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Tracks", len(tracks))
                    col2.metric("Exact Duplicates", len(exact))
                    col3.metric("Similar Tracks", len(similar))

                    # 2. PREPARE DATA FOR PANDAS DISPLAY & EXPORT
                    all_dupes_list = []
                    # Exact
                    for tid, dupes in exact.items():
                        for d in dupes:
                            all_dupes_list.append({**d, 'Type': 'Exact (Same ID)'})
                    # Similar
                    for key, dupes in similar.items():
                        for d in dupes:
                            # Avoid duplicates in the dataframe if they were already caught by 'exact'
                            if not any(x['id'] == d['id'] and x['position'] == d['position'] for x in all_dupes_list):
                                all_dupes_list.append({**d, 'Type': 'Similar (Name/Artist)'})

                    if not exact and not similar:
                        st.info("🎉 No duplicates found! Your playlist is clean.")
                    else:
                        # Create DataFrame
                        df = pd.DataFrame(all_dupes_list)
                        df = df[['position', 'name', 'artist', 'album', 'Type', 'id']]
                        df.columns = ['Pos', 'Track Name', 'Artist', 'Album', 'Match Type', 'Spotify ID']

                        # 3. VISUAL RESULTS (Expanders)
                        st.write("---")
                        st.subheader("🎵 Grouped Results")
                        tab1, tab2 = st.tabs(["❌ Exact Duplicates", "⚠️ Similar Tracks"])
                        
                        with tab1:
                            if exact:
                                for tid, dupes in exact.items():
                                    first = dupes[0]
                                    with st.expander(f"{first['name']} - {first['artist']}"):
                                        for d in dupes:
                                            st.write(f"• **Position {d['position']}** | Album: {d['album']}")
                            else:
                                st.write("No exact duplicates found.")

                        with tab2:
                            if similar:
                                for key, dupes in similar.items():
                                    first = dupes[0]
                                    with st.expander(f"{first['name']} - {first['artist']}"):
                                        for d in dupes:
                                            st.write(f"• **Position {d['position']}** | Album: {d['album']}")
                            else:
                                st.write("No similar tracks found.")

                        # 4. DATA TABLE PREVIEW (Pandas Display)
                        st.write("---")
                        st.subheader("📋 Data Preview")
                        st.write("Scroll through the table below to see all duplicate entries:")
                        st.dataframe(df, use_container_width=True, hide_index=True)

                        # 5. EXPORT OPTIONS
                        st.write("---")
                        st.subheader("💾 Export Results")
                        
                        col_dl1, col_dl2, col_dl3 = st.columns(3)
                        
                        # Prepare Text Export
                        export_text = "SPOTIFY DUPLICATE REPORT\n" + "="*25 + "\n\n"
                        for _, row in df.iterrows():
                            export_text += f"[{row['Match Type']}] Pos: {row['Pos']} | {row['Track Name']} - {row['Artist']} ({row['Album']})\n"

                        with col_dl1:
                            csv_data = df.to_csv(index=False).encode('utf-8')
                            st.download_button("📊 Download CSV", csv_data, "duplicates.csv", "text/csv", use_container_width=True)
                        
                        with col_dl2:
                            st.download_button("📥 Download TXT", export_text, "duplicates.txt", "text/plain", use_container_width=True)
                        
                        with col_dl3:
                            with st.popover("📋 Copy to Clipboard", use_container_width=True):
                                st.info("Copy the text below:")
                                st.code(export_text, language="text")
                
        except Exception as e:
            st.exception(e)

st.write("---")
st.caption("Built with Streamlit, Spotipy & Pandas")
