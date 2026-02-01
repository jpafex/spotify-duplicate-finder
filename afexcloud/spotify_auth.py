import streamlit as st
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import CacheHandler

class SessionCacheHandler(CacheHandler):
    """Store Spotipy token_info in Streamlit session_state only."""
    def __init__(self, key: str = "spotify_token_info"):
        self.key = key

    def get_cached_token(self):
        return st.session_state.get(self.key)

    def save_token_to_cache(self, token_info):
        st.session_state[self.key] = token_info

    def delete_cached_token(self):
        st.session_state[self.key] = None


def get_auth_manager() -> SpotifyOAuth:
    scope = "playlist-modify-public playlist-modify-private playlist-read-private"
    return SpotifyOAuth(
        client_id=st.secrets["SPOTIFY_CLIENT_ID"],
        client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"],
        redirect_uri=st.secrets["SPOTIFY_REDIRECT_URI"],
        scope=scope,
        open_browser=False,
        cache_handler=SessionCacheHandler(),
        show_dialog=False,
    )


def _get_query_params():
    try:
        return dict(st.query_params)
    except Exception:
        return st.experimental_get_query_params()


def _clear_query_params():
    try:
        st.query_params.clear()
    except Exception:
        st.experimental_set_query_params()


def handle_spotify_callback(auth_manager: SpotifyOAuth) -> None:
    """If we returned from Spotify with ?code=..., exchange it and rerun."""
    qp = _get_query_params()

    if "error" in qp:
        st.error(f"Spotify authorization error: {qp.get('error')}")
        _clear_query_params()
        return

    code = None
    if "code" in qp:
        code = qp["code"][0] if isinstance(qp["code"], list) else qp["code"]

    if not code:
        return

    try:
        # Exchange code for token_info; saved into session_state via cache_handler
        auth_manager.get_access_token(code, check_cache=False, as_dict=True)
        _clear_query_params()
        st.rerun()
    except Exception as e:
        st.error("Spotify login failed. Please try again.")
        st.caption(f"Details: {e}")
        _clear_query_params()


def get_valid_token_info(auth_manager: SpotifyOAuth):
    token_info = auth_manager.cache_handler.get_cached_token()
    return auth_manager.validate_token(token_info)


def get_connect_url(auth_manager: SpotifyOAuth) -> str:
    # For beta simplicity, let Spotipy create state internally and don't enforce validation.
    return auth_manager.get_authorize_url()
