import streamlit as st
from afexcloud.layout import bootstrap_page

st.set_page_config(page_title="AfexCloud Dashboard", page_icon="☁️", layout="wide")

bootstrap_page()

st.title("☁️ AfexCloud")
st.caption("Choose a tool from the left sidebar (Pages).")
