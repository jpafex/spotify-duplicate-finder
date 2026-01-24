import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from collections import defaultdict
import io

# Page config
st.set_page_config(page_title="Spotify Duplicate Finder", page_icon="🎵")

# Title
st.title("🎵 Spotify Duplicate Finder")
st.write("Find duplicate songs in your Spotify playlists")

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("App Controls")
    
    def reset_app():
        # 1. Clear the Spotify API cache
        st.cache_resource.clear()
        # 2. Clear the text input by resetting its session state key
        if 'playlist_input' in st.session_state:
            st.session_state['playlist_input'] = ""
        # 3. Rerun the app
        st.rerun()

    if st.button("🔄 Refresh / Clear All"):
        reset_app()
        
    st.info("This will clear the current results and reset the search box.")

# Spotify credentials from Streamlit secrets
try:
    CLIENT_ID = st.secrets["SPOTIFY_CLIENT_ID"]
    CLIENT_SECRET = st.secrets["SPOTIFY_CLIENT_SECRET"]
except KeyError:
    st.error("Missing Spotify Credentials! Please add them to your Streamlit Secrets.")
    st.stop()

# Initialize Spotify client
@st.cache_resource
def get_spotify_client():
    auth_manager = SpotifyClientCredentials(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
    return spotipy.Spotify(auth_manager=auth_manager)

sp = get_spotify_client()

def get_playlist_tracks(playlist_id):
    """Fetch all tracks from a playlist handling pagination."""
    tracks = []
    try:
        results = sp.playlist_tracks(playlist_id)
    except Exception as e:
        st.error(f"Failed to fetch playlist: {e}")
        return []
    
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
    
    return tracks

def find_duplicates(tracks):
    """Find duplicate tracks by ID and by name+artist."""
    by_id = defaultdict(list)
    by_name_artist = defaultdict(list)
    
    for i, track in enumerate(tracks):
        if track['id']:
            by_id[track['id']].append({**track, 'position': i + 1})
        
        key = f"{track['name'].lower()}::{track['artist'].lower()}"
        by_name_artist[key].append({**track, 'position': i + 1})
    
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
                    
                    st.success(f"✅ Analysis complete!")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Tracks", len(tracks))
                    with col2:
                        st.metric("Exact Duplicates", len(exact))
                    with col3:
                        st.metric("Similar Tracks", len(similar))
                    
                    # --- EXPORT LOGIC ---
                    export_text = "SPOTIFY DUPLICATE REPORT\n" + "="*25 + "\n\n"
                    
                    if exact:
                        export_text += "EXACT DUPLICATES (Same Track ID):\n"
                        for tid, dupes in exact.items():
                            export_text += f"- {dupes[0]['name']} by {dupes[0]['artist']}\n"
                            for d in dupes:
                                export_text += f"  • Position: {d['position']} | Album: {d['album']}\n"
                        export_text += "\n"

                    if similar:
                        export_text += "SIMILAR TRACKS (Same Name & Artist):\n"
                        for key, dupes in similar.items():
                            export_text += f"- {dupes[0]['name']} by {dupes[0]['artist']}\n"
                            for d in dupes:
                                export_text += f"  • Position: {d['position']} | Album: {d['album']}\n"
                        export_text += "\n"

                    # Only show export options if duplicates exist
                    if exact or similar:
                        st.write("---")
                        st.subheader("💾 Export Results")
                        
                        # Download Button
                        st.download_button(
                            label="📥 Download as Text File",
                            data=export_text,
                            file_name="spotify_duplicates.txt",
                            mime="text/plain"
                        )
                        
                        # Copy to Clipboard (using st.code for the built-in copy button)
                        with st.expander("📋 Click to Copy to Clipboard"):
                            st.info("Hover over the box below and click the copy icon in the top right.")
                            st.code(export_text, language="text")

                    # --- VISUAL DISPLAY ---
                    if exact:
                        st.write("---")
                        st.subheader("❌ Exact Duplicates (Same ID)")
                        for track_id, dupes in exact.items():
                            first = dupes[0]
                            with st.expander(f"🎵 {first['name']} - {first['artist']}"):
                                for d in dupes:
                                    st.write(f"• **Position {d['position']}** | Album: {d['album']}")
                    
                    if similar:
                        st.write("---")
                        st.subheader("⚠️ Similar Tracks (Same Name & Artist)")
                        for key, dupes in similar.items():
                            if len(dupes) > 1:
                                first = dupes[0]
                                with st.expander(f"🎵 {first['name']} - {first['artist']}"):
                                    for d in dupes:
                                        st.write(f"• **Position {d['position']}** | Album: {d['album']}")
                    
                    if not exact and not similar:
                        st.info("🎉 No duplicates found! Your playlist is clean.")
                
        except Exception as e:
            st.error("An error occurred during analysis.")
            st.exception(e) 

st.write("---")
st.caption("Built with Streamlit & Spotipy")
