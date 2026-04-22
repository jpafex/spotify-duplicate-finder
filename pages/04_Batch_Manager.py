import streamlit as st
import pandas as pd
import io
import zipfile
import sys
import os
import re
from math import ceil
import spotipy
from datetime import datetime

# Path Fix for 'pages' folder access
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from afexcloud.layout import bootstrap_page
# Import the maze-buster utilities
from spotify_utils import get_playlist_data, get_track_info, process_exportify_csv

# 1. Page Config
st.set_page_config(page_title="Batch Manager | AfexCloud", page_icon="📦", layout="wide")

# 2. Bootstrap Style & Security
auth_manager, token_info = bootstrap_page()

# Initialize Session State for batch data
if "batch_df" not in st.session_state:
    st.session_state["batch_df"] = None

# 3. Tool Logic
st.title("📦 Batch Manager")

# --- NEWBIE GUIDE & EXPORTIFY LINK ---
with st.expander("🆕 New here? How to batch-process client playlists", expanded=True):
    st.markdown("""
    Because of the **2026 Spotify rules**, the API cannot "see" playlists you don't own. 
    1.  **Export the client's playlist** as a CSV using [Exportify.net](https://exportify.net/).
    2.  **Upload the CSV** below to bypass ownership restrictions and see BPM data.
    3.  **Slice** the data into batches or **Push** them as new playlists to your account.
    """)
    st.link_button("🔗 Go to Exportify.net", "https://exportify.net/")

tab1, tab2 = st.tabs(["🗂️ Create Batches", "🚀 Bulk Create Playlists"])

with tab1:
    st.subheader("Step 1: Ingest Playlist Data")
    
    # Path A: CSV Upload (Maze-Buster Path)
    uploaded_csv = st.file_uploader("Upload Exportify CSV (Recommended)", type=["csv"], key="batch_csv")
    
    # Path B: API URL (Fallback Path)
    st.write("---")
    url_input = st.text_input("OR Enter Playlist URL/ID (API Path - Ownership required):")
    
    if st.button("🔍 Load Data for Batching"):
        if uploaded_csv:
            with st.spinner("Processing CSV..."):
                st.session_state["batch_df"] = process_exportify_csv(uploaded_csv)
                # Store the playlist name for file naming
                st.session_state["batch_p_name"] = uploaded_csv.name.rsplit('.', 1)[0]
                st.success(f"Loaded {len(st.session_state['batch_df'])} tracks from CSV.")
        elif url_input and token_info:
            with st.spinner("Fetching from API..."):
                try:
                    sp = spotipy.Spotify(auth_manager=auth_manager)
                    p_id = url_input.split('/')[-1].split('?')[0] if '/' in url_input else url_input
                    res = sp.playlist(p_id)
                    st.session_state["batch_p_name"] = res['name']
                    
                    content = get_playlist_data(res)
                    items = content.get('items', [])
                    
                    parsed = []
                    for idx, item in enumerate(items):
                        t = get_track_info(item)
                        if t:
                            parsed.append({
                                'Name': t.get('name', 'Unknown'),
                                'Artist': ", ".join([a['name'] for a in t.get('artists', [])]),
                                'Album': t.get('album', {}).get('name', 'Unknown'),
                                'Spotify-id': t.get('id')
                            })
                    
                    if parsed:
                        st.session_state["batch_df"] = pd.DataFrame(parsed)
                        st.success(f"Loaded {len(parsed)} tracks from API.")
                    else:
                        st.warning("No tracks found. (2026 Rule: You must own the playlist to use the API path).")
                except Exception as e:
                    st.error(f"API Error: {e}")
        else:
            st.error("Please provide a CSV or a URL (and ensure Spotify is connected).")

    # Display and Batching Logic
    if st.session_state["batch_df"] is not None:
        df = st.session_state["batch_df"]
        st.write("---")
        st.subheader("Step 2: Define Batch Size")
        batch_size = st.number_input("Tracks per Batch:", min_value=1, value=50)
        
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        if st.button("📦 PREPARE BATCH ZIP"):
            total = len(df)
            num_batches = ceil(total / batch_size)
            
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zf:
                for i in range(num_batches):
                    batch_data = df.iloc[i*batch_size : (i+1)*batch_size]
                    
                    # Formatting filename with Playlist Name and Batch Number
                    p_name_safe = re.sub(r'[^a-zA-Z0-9_]', '_', st.session_state.get("batch_p_name", "Playlist"))
                    safe_proj = re.sub(r'[^a-zA-Z0-9_]', '_', st.session_state.get("global_proj", "Project"))
                    
                    start_n = (i * batch_size) + 1
                    end_n = min((i + 1) * batch_size, total)
                    file_label = f"Batch_{i+1}_Pos_{start_n}_to_{end_n}"
                    
                    csv_name = f"AfexCloud_{safe_proj}_{p_name_safe}_{file_label}.csv"
                    zf.writestr(csv_name, batch_data.to_csv(index=False).encode('utf-8'))
            
            st.download_button(
                label=f"📥 Download {num_batches} Batches (ZIP)",
                data=zip_buffer.getvalue(),
                file_name=f"AfexCloud_{safe_proj}_Batches.zip",
                mime="application/zip"
            )

with tab2:
    st.subheader("🚀 Bulk Create Playlists on Your Account")
    st.info("This tool turns your Batch CSVs into actual Spotify playlists on your Premium account.")
    
    if not token_info:
        st.warning("Connect Spotify first via the sidebar.")
    else:
        sp = spotipy.Spotify(auth_manager=auth_manager)
        user_id = sp.current_user()["id"]
        
        files = st.file_uploader("Upload Batch CSVs to create as playlists", accept_multiple_files=True, type="csv")
        
        if st.button("🔥 PUSH TO SPOTIFY"):
            if files:
                progress_bar = st.progress(0)
                for idx, f in enumerate(files):
                    # Use the clean CSV processor
                    df_b = pd.read_csv(f)
                    
                    # Ensure we have the ID column (Exportify or Afex format)
                    id_col = 'Spotify-id' if 'Spotify-id' in df_b.columns else 'Spotify ID'
                    
                    if id_col in df_b.columns:
                        # Dynamic Playlist Name
                        p_name = f"{st.session_state.get('global_proj','')} - {f.name.replace('.csv','')}"
                        new_p = sp.user_playlist_create(user=user_id, name=p_name, public=False)
                        
                        # Clean URIs for adding
                        uris = [tid if tid.startswith('spotify:track:') else f"spotify:track:{tid}" 
                                for tid in df_b[id_col].dropna().tolist()]
                        
                        # Add in batches of 100 for safety
                        for i in range(0, len(uris), 100):
                            sp.playlist_add_items(new_p['id'], uris[i:i+100])
                        
                        st.write(f"✅ Created: {p_name}")
                    
                    progress_bar.progress((idx + 1) / len(files))
                st.success(f"Successfully pushed {len(files)} playlists to your account!")
                st.balloons()
            else:
                st.error("No files uploaded.")
