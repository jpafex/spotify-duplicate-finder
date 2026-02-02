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

# Initialize Session State for the batch data
if "batch_df" not in st.session_state:
    st.session_state["batch_df"] = None

# 3. Helper: Fetch Tracks from Spotify URL
def get_tracks_from_url(sp, url_or_id):
    p_id = url_or_id.split('/')[-1].split('?')[0] if '/' in url_or_id else url_or_id
    try:
        results = sp.playlist_tracks(p_id)
        tracks = []
        pos = 1
        while results:
            for item in results['items']:
                if item.get('track'):
                    t = item['track']
                    tracks.append({
                        'Original Pos': pos,
                        'Spotify ID': t.get('id'), 
                        'Name': t.get('name', 'Unknown'), 
                        'Artist': t['artists'][0]['name'] if t.get('artists') else 'Unknown'
                    })
                    pos += 1
            results = sp.next(results) if results['next'] else None
        return pd.DataFrame(tracks)
    except Exception as e:
        st.error(f"Spotify Error: {e}")
        return None

# 4. Tool Interface
st.title("📦 Batch Manager")
st.info("State-Persistence Active: Fetched tracks are now 'locked in' until you reset the project.")

tab1, tab2 = st.tabs(["Step 1: Create Batches", "Step 2: Upload to Spotify"])
safe_proj = st.session_state.get("_safe_proj", "project")

with tab1:
    st.subheader("📁 Create Mini-Sets")
    
    input_type = st.radio("Choose Input Type:", ["Spotify Playlist URL", "Upload Master Log (CSV)"], horizontal=True)
    
    if input_type == "Spotify Playlist URL":
        url = st.text_input("🔗 Paste Spotify Playlist URL or ID:")
        if st.button("🔍 Fetch Tracks"):
            if not token_info:
                st.warning("Please connect Spotify in the sidebar first.")
            else:
                sp = spotipy.Spotify(auth=token_info['access_token'])
                # Store directly in session state so it survives the next click
                st.session_state["batch_df"] = get_tracks_from_url(sp, url)
    else:
        master_f = st.file_uploader("📤 Upload Master Log (CSV)", type="csv")
        if master_f:
            # Store upload in session state
            st.session_state["batch_df"] = pd.read_csv(master_f)

    # --- THE PERSISTENT LOGIC BLOCK ---
    if st.session_state["batch_df"] is not None:
        df = st.session_state["batch_df"]
        
        # Robust Mapping for 'ellie half 2.csv' and others
        mapping = {
            'Spotify - id': 'Spotify ID',
            'track_id': 'Spotify ID',
            'track_name': 'Name',
            'artists': 'Artist'
        }
        df = df.rename(columns=mapping)
        
        if 'Spotify ID' not in df.columns:
            st.error(f"Column Error: Could not find 'Spotify ID'. Found: {list(df.columns)}")
        else:
            total = len(df)
            batch_size = 25
            num_batches = ceil(total / batch_size)
            
            st.write(f"✅ Tracks Ready: **{total}** | Potential Batches: **{num_batches}**")
            st.dataframe(df.head(5), use_container_width=True) # Preview for confidence
            
            # This click will now work because df is pulled from Session State
            if st.button("📦 Generate Zip of 25-Song Sets"):
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for i in range(num_batches):
                        batch_data = df.iloc[i * batch_size : (i + 1) * batch_size]
                        start_n = (i * batch_size) + 1
                        end_n = min((i + 1) * batch_size, total)
                        lbl = f"{start_n}_to_{end_n}"
                        zf.writestr(f"{safe_proj}_Batch_{i+1}_{lbl}.csv", batch_data.to_csv(index=False).encode('utf-8'))
                
                st.download_button(
                    "📥 DOWNLOAD BATCH ZIP", 
                    zip_buffer.getvalue(), 
                    f"{safe_proj}_Batches.zip", 
                    "application/zip"
                )

with tab2:
    st.subheader("🚀 Bulk Create Playlists")
    if not token_info:
        st.warning("Connect Spotify first.")
    else:
        files = st.file_uploader("Upload Batch CSVs", accept_multiple_files=True, type="csv")
        if st.button("🔥 PUSH TO SPOTIFY"):
            if files:
                sp = spotipy.Spotify(auth=token_info['access_token'])
                u_id = sp.current_user()["id"]
                for f in files:
                    df_b = pd.read_csv(f).rename(columns=mapping)
                    p_name = f"{st.session_state.get('global_proj','')} - {f.name.replace('.csv','')}"
                    new_p = sp.user_playlist_create(user=u_id, name=p_name, public=False)
                    uris = [f"spotify:track:{tid}" for tid in df_b['Spotify ID'].tolist() if pd.notnull(tid)]
                    sp.playlist_add_items(new_p["id"], uris)
                    st.write(f"✅ Created: {p_name}")
                st.balloons()
