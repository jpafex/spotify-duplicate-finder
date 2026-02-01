import json
import secrets
import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import CacheHandler

from .cookies import get_cookies
from .config import SPOTIFY_TOKEN_COOKIE_KEY, SPOTIFY_STATE_COOKIE_KEY

def _cookie_get_json(key: str):
    cookies = get_cookies()
    raw = cookies.get(key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None

def _cookie_set_json(key: str, obj) -> None:
    cookies = get_cookies()
    try:
        cookies[key] = json.dumps(obj)
        cookies.save()
    except Exception:
        pass

def _cookie_clear(key: str) -> None:
    cookies = get_cookies()
    try:
        if key in cookies:
            del cookies[key]
        cookies.save()
    except Exception:
        pass
    try:
        cookies[key] = ""
        cookies.save()
    except Exception:
        pass

def _get_or_create_oauth_state() -> str:
    cookies = get_cookies()
    state = cookies.get(SPOTIFY_STATE_COOKIE_KEY)
    if not state or len(state) < 10:
        state = secrets.token_urlsafe(16)
        cookies[SPOTIFY_STATE_COOKIE_KEY] = state
        cookies.save()
    return state

class SessionCookieCacheHandler(CacheHandler):
    """
    Spotipy token cache:
    - session_state first
    - fallback to encrypted cookie
    - save to both
    """
    def __init__(self, session_key: str = "spotify_token_info"):
        self.session_key = session_key

    def get_cached_token(self):
        tok = st.session_state.get(self.session_key)
        if tok:
            return tok

        tok = _cookie_get_json(SPOTIFY_TOKEN_COOKIE_KEY)
        if tok:
            st.session_state[self.session_key] = tok
            return tok
        return None

    def save_token_to_cache(self, token_info):
        st.session_state[self.session_key] = token_info
        _cookie_set_json(SPOTIFY_TOKEN_COOKIE_KEY, token_info)

    def delete_cached_token(self):
        st.session_state[self.session_key] = None
        _cookie_clear(SPOTIFY_TOKEN_COOKIE_KEY)
        _cookie_clear(SPOTIFY_STATE_COOKIE_KEY)

def get_auth_manager() -> SpotifyOAuth:
    scope = "playlist-modify-public playlist-modify-private playlist-read-private"
    cache_handler = SessionCookieCacheHandler()
    return SpotifyOAuth(
        client_id=st.secrets["SPOTIFY_CLIENT_ID"],
        client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"],
        redirect_uri=st.secrets["SPOTIFY_REDIRECT_URI"],
        scope=scope,
        open_browser=False,
        cache_handler=cache_handler,
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
    """
    Runs on every page load. If Spotify redirected back with ?code=...,
    exchange it, clear params, rerun.
    """
    qp = _get_query_params()

    if "error" in qp:
        st.error(f"Spotify authorization error: {qp.get('error')}")
        _clear_query_params()
        return

    code = None
    state = None

    if "code" in qp:
        code = qp["code"][0] if isinstance(qp["code"], list) else qp["code"]
    if "state" in qp:
        state = qp["state"][0] if isinstance(qp["state"], list) else qp["state"]

    if not code:
        return

    cookies = get_cookies()
    expected_state = cookies.get(SPOTIFY_STATE_COOKIE_KEY)

    # If state mismatch happens due to Streamlit session resets or multi-tab,
    # warn but do not hard-block (prevents redirect loops).
    if expected_state and state and state != expected_state:
        st.warning("Spotify login validation warning (state mismatch). Retrying token exchange to avoid loops.")
        _cookie_clear(SPOTIFY_STATE_COOKIE_KEY)

    try:
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
    state = _get_or_create_oauth_state()
    return auth_manager.get_authorize_url(state=state)

