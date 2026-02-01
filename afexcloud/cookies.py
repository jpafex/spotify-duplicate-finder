import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager
from .config import COOKIE_PREFIX

_COOKIE_STATE_KEY = "_afexcloud_cookie_manager"

def get_cookies() -> EncryptedCookieManager:
    # Create once per Streamlit session (prevents DuplicateElementKey)
    if _COOKIE_STATE_KEY not in st.session_state:
        st.session_state[_COOKIE_STATE_KEY] = EncryptedCookieManager(
            prefix=COOKIE_PREFIX,
            password=st.secrets.get("COOKIES_PASSWORD", "CHANGE_ME_SET_COOKIES_PASSWORD"),
        )

    cookies = st.session_state[_COOKIE_STATE_KEY]

    # IMPORTANT: show something before stopping, so users aren’t confused
    if not cookies.ready():
        st.info("Loading secure session…")
        st.stop()

    return cookies
