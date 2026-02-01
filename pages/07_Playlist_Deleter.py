import streamlit as st
import pandas as pd
import spotipy
from datetime import datetime

from afexcloud.layout import bootstrap_page
from afexcloud.spotify_auth import get_auth_manager, get_valid_token_info

bootstrap_page()

st.title("🗑️ Playlist Deleter")

auth_manager = get_auth_manager()
token_info = get_valid_token_info(auth_manager)

if not token_info:
    st.warning("Connect Spotify first (sidebar).")
else:
    sp = spotipy.Spotify(auth_manager=auth_manager)

    if st.button("🔍 Load My Playlists"):
        st.session_state["my_playlists"] = sp.current_user_playlists(limit=50)["items"]

    if "my_playlists" in st.session_state:
        with st.form("del_form"):
            to_del = []
            for p in st.session_state["my_playlists"]:
                if st.checkbox(f"{p['name']} (ID: {p['id']})"):
                    to_del.append({"id": p["id"], "name": p["name"]})

            if st.form_submit_button("🔥 DELETE SELECTED"):
                for item in to_del:
                    sp.current_user_unfollow_playlist(item["id"])

                st.success(f"Deleted {len(to_del)} playlists.")
                log = pd.DataFrame(to_del)

                st.download_button(
                    "📥 Download Deletion Proof",
                    log.to_csv(index=False).encode("utf-8"),
                    f"Deletion_Proof_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                )

                del st.session_state["my_playlists"]
                st.rerun()

