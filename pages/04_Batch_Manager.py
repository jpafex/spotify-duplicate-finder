import streamlit as st
import pandas as pd
import io
import zipfile
from math import ceil
import spotipy

from afexcloud.layout import bootstrap_page
from afexcloud.spotify_auth import get_auth_manager, get_valid_token_info
from afexcloud.utils import get_playlist_metadata

bootstrap_page()

st.title("📦 Batch Manager")
tab1, tab2 = st.tabs(["Step 1: Create Batches", "Step 2: Upload"])

safe_proj = st.session_state.get("_safe_proj", "project")

with tab1:
    url = st.text_input("Source Playlist URL/ID:")
    if st.button("Generate Batches"):
        _, all_tracks = get_playlist_metadata(
            url_or_id=url,
            client_id=st.secrets["SPOTIFY_CLIENT_ID"],
            client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"],
        )
        if not all_tracks:
            st.warning("No tracks found.")
        else:
            num_batches = ceil(len(all_tracks) / 25)
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for i in range(num_batches):
                    batch = all_tracks[i * 25 : (i + 1) * 25]
                    df_batch = pd.DataFrame(batch)[["Original Pos", "Name", "Artist", "Album", "Spotify - id"]]
                    lbl = f"{batch[0]['Original Pos']}_to_{batch[-1]['Original Pos']}"
                    zf.writestr(
                        f"{safe_proj}_Batch_{i+1}_{lbl}.csv",
                        df_batch.to_csv(index=False).encode("utf-8"),
                    )

            st.download_button(
                "📦 DOWNLOAD ZIP",
                zip_buffer.getvalue(),
                f"{safe_proj}_Batches.zip",
                "application/zip",
            )

with tab2:
    auth_manager = get_auth_manager()
    token_info = get_valid_token_info(auth_manager)

    if not token_info:
        st.warning("Connect Spotify first (sidebar).")
    else:
        files = st.file_uploader("Upload Batch CSVs", accept_multiple_files=True, type="csv")
        if st.button("🚀 Create Spotify Playlists"):
            if not files:
                st.warning("Please upload at least one CSV batch file.")
            else:
                sp_write = spotipy.Spotify(auth_manager=auth_manager)
                user_id = sp_write.current_user()["id"]

                for uploaded in files:
                    df = pd.read_csv(uploaded)
                    playlist = sp_write.user_playlist_create(
                        user=user_id,
                        name=f"{st.session_state.get('global_proj','')}: {uploaded.name}",
                        public=False,
                    )
                    track_uris = [f"spotify:track:{tid}" for tid in df["Spotify - id"].tolist()]
                    for start in range(0, len(track_uris), 100):
                        sp_write.playlist_add_items(playlist["id"], track_uris[start : start + 100])

                st.balloons()
                st.success("Playlists created.")

