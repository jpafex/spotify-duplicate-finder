import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from collections import defaultdict

# Page config
st.set_page_config(page_title="Spotify Duplicate Finder", page_icon="🎵")

# Title
st.title("🎵 Spotify Duplicate Finder")
st.write("Find duplicate songs in your Spotify playlists")

# Spotify credentials from Streamlit secrets
# Ensure these keys exist in your Streamlit Cloud "Secrets" setting
try:
    CLIENT_ID = st.secrets["SPOTIFY_CLIENT_ID"]
    CLIENT_SECRET = st.secrets["SPOTIFY_CLIENT_SECRET"]
except KeyError:
    st.error("Missing Spotify Credentials! Please add them to your Streamlit Secrets.")
    st.stop()

# Initialize Spotify client
@st.cache_resource
def get_spotify_client():
    """
    Using SpotifyClientCredentials for read-only access to public playlists.
    This does not require a redirect URI or user login.
    """
    auth_manager = SpotifyClientCredentials(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
    return spotipy.Spotify(auth_manager=auth_manager)

sp = get_spotify_client()

def get_playlist_tracks(playlist_id):
    """Fetch all tracks from a playlist handling pagination."""
    tracks = []
    results = sp.playlist_tracks(playlist_id)
    
    while results:
        for item in results['items']:
            # Ensure the track exists (sometimes tracks are deleted/unavailable)
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
        # Only track by ID if an ID exists
        if track['id']:
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
            # Enhanced Playlist ID Extraction
            # Handles: open.spotify.com/playlist/ID or just the ID itself
            if 'spotify.com' in playlist_url:
                # Splits the URL and grabs the ID before any query parameters (?)
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
                st.subheader("❌ Exact Duplicates (Same ID)")
                for track_id, dupes in exact.items():
                    first = dupes[0]
                    with st.expander(f"🎵 {first['name']} - {first['artist']}"):
                        for d in dupes:
                            st.write(f"• **Position {d['position']}** | Album: {d['album']}")
            
            # Similar tracks section
            if similar:
                st.write("---")
                st.subheader("⚠️ Similar Tracks (Same Name & Artist)")
                for key, dupes in similar.items():
                    # Only show if not already caught by "Exact" match
                    if len(dupes) > 1:
                        first = dupes[0]
                        with st.expander(f"🎵 {first['name']} - {first['artist']}"):
                            for d in dupes:
                                st.write(f"• **Position {d['position']}** | Album: {d['album']}")
            
            # No duplicates message
            if not exact and not similar:
                st.info("🎉 No duplicates found! Your playlist is clean.")
                
        except Exception as e:
            # Using st.exception provides the traceback which is crucial 
            # for identifying why you are getting "Address already in use"
            st.error("An error occurred during analysis.")
            st.exception(e) 

# Footer
st.write("---")
st.caption("Built with Streamlit & Spotipy")
