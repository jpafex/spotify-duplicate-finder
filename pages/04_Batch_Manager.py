import streamlit as st
import pandas as pd
import io
import zipfile
from math import ceil
import spotipy
import re

from afexcloud.layout import bootstrap_page
from afexcloud.spotify_auth import get_auth_manager, get_valid_token_info

# 1. Page Config
st.set_page_config(page_title="Batch Manager | AfexCloud", page_icon="📦", layout="wide")

# 2. Bootstrap Style & Security
auth_manager, token_info = bootstrap_page()

# 3. Tool Logic
st.title("📦 Batch Manager")
st.info("Split your 1990s Master Log into 25-song batches for easier party management.")

tab1, tab2 = st.tabs(["Step 1: Create Batches", "Step 2: Upload to Spotify"])

safe_proj = st.session_state.get("_safe_proj", "project")

with tab1:
    st.subheader("📁 Create Mini-Sets from Master Log")
    master_f = st.file_uploader("Upload your Master DJ Log (CSV)", type="csv")
    
    if master_f:
        df_master = pd.read_csv(master_f)
        
        # Standardize columns to match our Bridge output
        mapping = {'track_name': 'Name', 'artists': 'Artist', 'track_id': 'Spotify ID'}
        df_master = df_master.rename(columns={k: v for k, v in mapping.items() if k in df_master.columns})
        
        if 'Spotify ID' not in df_master.columns:
            st.error("The CSV must have a 'Spotify ID' or 'track_id' column to create batches.")
        else:
            total_tracks = len(df_master)
            batch_size = 25
            num_batches = ceil(total_tracks / batch_size)
            
            st.write(f"Total Tracks: **{total_tracks}** | Resulting Batches: **{num_batches}**")
            
            if st.button("📦 Generate Zip of Batches"):
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for i in range(num_batches):
                        batch = df_master.iloc[i * batch_size : (i + 1) * batch_size]
                        
                        # Define batch labels (e.g., 1_to_25)
                        start_num = (i * batch_size) + 1
                        end_num = min((i + 1) * batch_size, total_tracks)
                        lbl = f"{start_num}_to_{end_num}"
                        
                        # Create CSV for this batch
                        batch_csv = batch.to_csv(index=False).encode('utf-8')
                        zf.writestr(f"{safe_proj}_Batch_{i+1}_{lbl}.csv", batch_csv)
                
                st.download_button(
                    "📥 DOWNLOAD BATCHES (ZIP)",
                    zip_buffer.getvalue(),
                    f"{safe_proj}_Batches.zip",
                    "application/zip"
                )

with tab2:
    st.subheader("🚀 Bulk Create Playlists")
    if not token_info:
        st.warning("Connect Spotify in the sidebar to upload batches.")
    else:
        files = st.file_uploader("Upload the Batch CSVs from your Zip", accept_multiple_files=True, type="csv")
        
        if st.button("🔥 CREATE SPOTIFY PLAYLISTS"):
            if not files:
                st.warning("No files uploaded.")
            else:
                sp = spotipy.Spotify(auth=token_info['access_token'])
                user_id = sp.current_user()["id"]
                
                for uploaded in files:
                    df_batch = pd.read_csv(uploaded)
                    
                    # Ensure we have the right ID column
                    id_col = 'Spotify ID' if 'Spotify ID' in df_batch.columns else 'track_id'
                    
                    if id_col in df_batch.columns:
                        # Create the Playlist
                        p_name = f"{st.session_state.get('global_proj','')} - {uploaded.name.split('.')[0]}"
                        new_p = sp.user_playlist_create(user=user_id, name=p_name, public=False)
                        
                        # Add tracks (Spotify allows 100 at a time, we are doing 25)
                        uris = [f"spotify:track:{tid}" for tid in df_batch[id_col].tolist() if pd.notnull(tid)]
                        sp.playlist_add_items(new_p["id"], uris)
                        st.write(f"✅ Created: {p_name}")
                
                st.balloons()
                st.success("All batches are now live in your Spotify library!")
