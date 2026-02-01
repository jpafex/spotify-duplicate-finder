import streamlit as st
from afexcloud.layout import bootstrap_page

# This ensures cookies + login + spotify callback handling are available everywhere.
bootstrap_page()

st.title("☁️ AfexCloud")
st.caption("Use the page selector in the left sidebar to choose a tool.")
st.info("If you just deployed this refactor: open any tool page from the sidebar.")

