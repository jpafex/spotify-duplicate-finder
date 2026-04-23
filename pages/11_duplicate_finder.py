import streamlit as st
import pandas as pd
import re
import sys
import os
from datetime import datetime
import spotipy
from collections import defaultdict

# Path Fix
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from afexcloud.layout import bootstrap_page
from spotify_utils import process_exportify_csv

# 1. Page Config
st.set_page_config(page_title="Duplicate Finder | AfexCloud", page_icon="🔍", layout="wide")
auth_manager, token_info = bootstrap_page()

st.title("🔍 Duplicate Finder & Cleaner")

# --- NEWBIE GUIDE ---
with st.expander("🆕 How to 'Clean' a Client Playlist", expanded=False):
    st.markdown("""
    1.  **Upload** the Exportify CSV.
    2.  The tool identifies duplicates (redundant copies).
    3.  The **'Push'** button creates a new playlist on your account with **only unique songs** (e.g., 167 total becomes 153 unique).
    """)

st.write("---")

uploaded_file = st.file_uploader("Upload Exportify CSV", type=["csv"])

if uploaded_file:
    raw_filename = uploaded_file.name.rsplit('.', 1)[0]
    
    with st.spinner("Analyzing tracks..."):
        df_csv = process_exportify_csv(uploaded_file)
        total_count = len(df_csv)
        
        # LOGIC: Separate the 'First Occurrences' from the 'Extras'
        unique_rows = []
        duplicate_rows = []
        seen_ids = set()

        for idx, row in df_csv.iterrows():
            tid = row['Spotify-id']
            if tid not in seen_ids:
                unique_rows.append(row) # This builds your 153-song list
                seen_ids.add(tid)
            else:
                duplicate_rows.append(row) # This builds your 14-song 'extras' list

        # 1. Display Audit Summary
        c1, c2, c3 = st.columns(3)
        c1.metric("Original Total", total_count)
        c2.metric("Duplicates Found", len(duplicate_rows), delta_color="inverse")
        c3.metric("Cleaned Result", len(unique_rows))

        # 2. Show the Duplicates (The "Redundant" tracks we are removing)
        if duplicate_rows:
            with st.expander(f"🚩 View {len(duplicate_rows)} Duplicates to be removed", expanded=True):
                df_dupes = pd.DataFrame(duplicate_rows)
                df_dupes.insert(0, 'Pos', range(1, len(df_dupes) + 1))
                df_dupes['BPM'] = df_dupes['BPM'].astype(str)
                st.dataframe(df_dupes, use_container_width=True, hide_index=True)
                
                # Download Report
                st.download_button(
                    "📥 Download Duplicate Audit Report",
                    data=df_dupes.to_csv(index=False).encode('utf-8'),
                    file_name=f"Audit_Duplicates_{raw_filename}.csv"
                )

        st.write("---")

        # 3. PUSH THE CLEANED LIST (The 153 Songs)
        st.subheader("🚀 Step 2: Push Cleaned Playlist")
        st.write(f"This will create a new playlist on your account with **{len(unique_rows)} unique songs**.")
        
        new_p_name = st.text_input("New Playlist Name:", value=f"Cleaned - {raw_filename}")
        
        if st.button("🔥 CREATE CLEANED PLAYLIST ON MY ACCOUNT"):
            if not token_info:
                st.error("Connect Spotify first via the sidebar.")
            else:
                try:
                    sp = spotipy.Spotify(auth_manager=auth_manager)
                    
                    # Create the new playlist
                    new_p = sp.current_user_playlist_create(name=new_p_name, public=False)
                    
                    # Gather URIs for ALL unique songs (the 153 tracks)
                    uris = [r['Spotify-id'] if str(r['Spotify-id']).startswith('spotify:track:') 
                            else f"spotify:track:{r['Spotify-id']}" for r in unique_rows]
                    
                    # Push in batches of 100
                    for i in range(0, len(uris), 100):
                        batch = uris[i:i+100]
                        sp._post(f"playlists/{new_p['id']}/items", payload={"uris": batch})
                    
                    st.success(f"Successfully created '{new_p_name}' with {len(unique_rows)} unique tracks!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Push failed: {e}")
