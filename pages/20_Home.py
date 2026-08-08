import streamlit as st
from afexcloud.layout import bootstrap_page

bootstrap_page()

st.title("🚀 AfexCloud Dashboard")
proj = st.session_state.get("global_proj") or "None Set"
st.info(f"Active Project: **{proj}**")

