import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager
from .config import COOKIE_PREFIX

_COOKIE_STATE_KEY = "_afexcloud_cookie_manager"

def get_cookies() -> EncryptedCookieManager:
    # Create once per Streamlit session and reuse (prevents DuplicateElementKey)
    if _COOKIE_STATE_KEY not in st.session_state:
        st.session_state[_COOKIE_STATE_KEY] = EncryptedCookieManager(
            prefix=COOKIE_PREFIX,
            password=st.secrets.get("COOKIES_PASSWORD", "CHANGE_ME_SET_COOKIES_PASSWORD"),
        )

    cookies = st.session_state[_COOKIE_STATE_KEY]

    # This must be called after creation; stop until component is ready
    if not cookies.ready():
        st.stop()

    return cookies
