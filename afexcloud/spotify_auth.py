import streamlit as st
from spotipy.oauth2 import SpotifyOAuth

def get_auth_manager():
    """Manages the Spotify Connection and Permissions (Scopes)."""
    # user-library-read is required to fetch Audio Features (Key/BPM)
    scope = "playlist-modify-public playlist-modify-private playlist-read-private user-library-read"
    
    return SpotifyOAuth(
    client_id=st.secrets["SPOTIFY_CLIENT_ID"],
    client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"],
    redirect_uri=st.secrets["SPOTIFY_REDIRECT_URI"],
    scope="playlist-modify-public playlist-modify-private playlist-read-private",
    show_dialog=True # Forces a clean handshake UI if their old session died
)

def handle_spotify_callback(auth_manager):
    """Captures the 'code' from the URL after the Lark clicks 'Agree'."""
    if "code" in st.query_params:
        auth_manager.get_access_token(st.query_params.get("code"), as_dict=False)
        st.query_params.clear()

def get_valid_token_info(auth_manager):
    """Checks if we have a working, non-expired key to Spotify."""
    if auth_manager is None:
        return None
    return auth_manager.validate_token(auth_manager.cache_handler.get_cached_token())

def get_connect_url(auth_manager):
    """Generates the 'Connect Spotify' link for the sidebar."""
    if auth_manager is None:
        return "#"
    return auth_manager.get_authorize_url()
