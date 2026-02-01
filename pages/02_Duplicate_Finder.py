import streamlit as st
import pandas as pd
from collections import defaultdict

from afexcloud.layout import bootstrap_page
from afexcloud.utils import get_playlist_metadata

bootstrap_page()

st.title("🔍 Duplicate Finder")
url = st.text_input("Enter Playlist URL/ID:")

if st.button("Scan"):
    p_name, tracks = get_playlist_metadata(
        url_or_id=url,
        client_id=st.secrets["SPOTIFY_CLIENT_ID"],
        client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"],
    )
    if not tracks:
        st.warning("No tracks found (check playlist ID/URL).")
    else:
        by_id = defaultdict(list)
        for t in tracks:
            by_id[t["Spotify - id"]].append(t)
        dupes = [i for g in by_id.values() if len(g) > 1 for i in g]

        if dupes:
            st.warning(f"Found {len(dupes)} duplicates.")
            df_dupes = pd.DataFrame(dupes)
            st.dataframe(df_dupes, use_container_width=True, hide_index=True)

            safe_proj = st.session_state.get("_safe_proj", "project")
            st.download_button(
                "📥 Download Dupes",
                df_dupes.to_csv(index=False).encode("utf-8"),
                f"{safe_proj}_dupes.csv",
                "text/csv",
            )
        else:
            st.success("No duplicates found!")

