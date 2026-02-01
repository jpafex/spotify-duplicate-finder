import streamlit as st
import pandas as pd
from afexcloud.layout import bootstrap_page
from afexcloud.utils import get_playlist_metadata

bootstrap_page()

st.title("📋 Song Lister")
url = st.text_input("Enter Playlist URL/ID:")

if st.button("Generate Inventory"):
    p_name, tracks = get_playlist_metadata(
        url_or_id=url,
        client_id=st.secrets["SPOTIFY_CLIENT_ID"],
        client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"],
    )
    if not tracks:
        st.warning("No tracks found (check playlist ID/URL).")
    else:
        df = pd.DataFrame(tracks)
        st.dataframe(df, use_container_width=True, hide_index=True)

        safe_proj = st.session_state.get("_safe_proj", "project")
        st.download_button(
            "📥 Download Inventory",
            df.to_csv(index=False).encode("utf-8"),
            f"{safe_proj}_inventory.csv",
            "text/csv",
        )

