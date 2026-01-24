import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from collections import defaultdict

# Page config
st.set_page_config(page_title="Spotify Duplicate Finder", page_icon="🎵")

# Title
st.title("🎵 Spotify Duplicate Finder")
st.write("Find duplicate songs in your Spotify playlists")

# Spotify credentials from Streamlit secrets
CLIENT_ID = st.secrets["SPOTIFY_CLIENT_ID"]
CLIENT_SECRET = st.secrets["SPOTIFY_CLIENT_SECRET"]
# Use different redirect URI based on environment
import os
if os.getenv('STREAMLIT_RUNTIME_ENVIRONMENT') == 'cloud':
    REDIRECT_URI = 'https://spotify-duplicate-finder-jpafex.streamlit.app/'
else:
    REDIRECT_URI = 'http://127.0.0.1:8888/callback'

# Initialize Spotify client
@st.cache_resource
def get_spotify_client():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope='playlist-read-private playlist-read-collaborative'
    ))

sp = get_spotify_client()

# Functions from your original script
def get_playlist_tracks(playlist_id):
    """Fetch all tracks from a playlist."""
    tracks = []
    results = sp.playlist_tracks(playlist_id)
    
    while results:
        for item in results['items']:
            if item['track']:
                track = item['track']
                tracks.append({
                    'id': track['id'],
                    'name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'album': track['album']['name'],
                    'added_at': item['added_at']
                })
        
        results = sp.next(results) if results['next'] else None
    
    return tracks

def find_duplicates(tracks):
    """Find duplicate tracks by ID and by name+artist."""
    by_id = defaultdict(list)
    by_name_artist = defaultdict(list)
    
    for i, track in enumerate(tracks):
        by_id[track['id']].append({**track, 'position': i + 1})
        
        key = f"{track['name'].lower()}::{track['artist'].lower()}"
        by_name_artist[key].append({**track, 'position': i + 1})
    
    exact = {k: v for k, v in by_id.items() if len(v) > 1}
    similar = {k: v for k, v in by_name_artist.items() if len(v) > 1}
    
    return exact, similar

# Streamlit UI
st.write("---")

# Input for playlist URL
playlist_url = st.text_input(
    "Enter Spotify Playlist URL or ID:",
    placeholder="https://open.spotify.com/playlist/..."
)

# Analyze button
if st.button("🔍 Find Duplicates", type="primary"):
    if not playlist_url:
        st.error("Please enter a playlist URL or ID")
    else:
        try:
            # Extract playlist ID
            if 'spotify.com/playlist/' in playlist_url:
                playlist_id = playlist_url.split('/')[-1].split('?')[0]
            else:
                playlist_id = playlist_url
            
            # Show loading message
            with st.spinner("Analyzing playlist..."):
                tracks = get_playlist_tracks(playlist_id)
                exact, similar = find_duplicates(tracks)
            
            # Display results
            st.success(f"✅ Analysis complete!")
            
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Tracks", len(tracks))
            with col2:
                st.metric("Exact Duplicates", len(exact))
            with col3:
                st.metric("Similar Tracks", len(similar))
            
            # Exact duplicates section
            if exact:
                st.write("---")
                st.subheader("❌ Exact Duplicates")
                for track_id, dupes in exact.items():
                    first = dupes[0]
                    with st.expander(f"🎵 {first['name']} - {first['artist']}"):
                        for d in dupes:
                            st.write(f"• **Position {d['position']}** | Album: {d['album']}")
            
            # Similar tracks section
            if similar:
                st.write("---")
                st.subheader("⚠️ Similar Tracks (Same name & artist, different albums)")
                for key, dupes in similar.items():
                    first = dupes[0]
                    with st.expander(f"🎵 {first['name']} - {first['artist']}"):
                        for d in dupes:
                            st.write(f"• **Position {d['position']}** | Album: {d['album']}")
            
            # No duplicates message
            if not exact and not similar:
                st.info("🎉 No duplicates found! Your playlist is clean.")
                
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.write("Make sure the playlist URL is correct and you have access to it.")

# Footer
st.write("---")

st.caption("Built with Streamlit & Spotipy")
