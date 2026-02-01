import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager
from .config import COOKIE_PREFIX

def get_cookies() -> EncryptedCookieManager:
    cookies = EncryptedCookieManager(
        prefix=COOKIE_PREFIX,
        password=st.secrets.get("COOKIES_PASSWORD", "CHANGE_ME_SET_COOKIES_PASSWORD"),
    )
    if not cookies.ready():
        st.stop()
    return cookies

