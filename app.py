import streamlit as st
from afexcloud.layout import bootstrap_page

st.set_page_config(page_title="AfexCloud Dashboard", page_icon="☁️", layout="wide")

bootstrap_page()

# Explicitly define which pages to show in the sidebar menu during the demo.
# Any page NOT listed here will be automatically hidden from the committee!
pg = st.navigation(
    [
        st.Page("pages/Smart_Playlist.py", title="Smart Playlist", icon="🎧", default=True),
        # Add any other specific pages you want to show here, for example:
        # st.Page("pages/Batch_Manager.py", title="Batch Manager", icon="📁"),
    ],
    position="sidebar"
)

# Run the selected page
pg.run()
