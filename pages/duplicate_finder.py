import streamlit as st
import pandas as pd
import re
import unicodedata
from collections import defaultdict
import sys
import os
from datetime import datetime
import spotipy

# Path Fix for 'pages' folder access
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from afexcloud.layout import bootstrap_page
from spotify_utils import get_playlist_data, get_track_info, process_exportify_csv

# 1. Page Config
st.set_page_config(page_title="Duplicate Finder | AfexCloud", page_icon="🔍", layout="wide")

# 2. Bootstrap Style & Security
auth_manager, token_info = bootstrap_page()

# 3. Tool Helpers
def advanced_normalize(text):
    """Normalization logic to catch subtle duplicates."""
    if not isinstance(text, str): text = str(text)
    text = unicodedata.normalize('NFKD', text)
    text = "".join([c for c in text if not unicodedata.combining(c)])
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return re.sub(r'\s+', ' ', text).strip()

# 4. Tool Logic
st.title("🔍 Duplicate Finder")

with st.expander("🆕 Newbie Guide: Mirroring & Cleaning", expanded=False):
    st.markdown("""
    1.  **Export** the client playlist via [Exportify.net](https://exportify.net/).
    2.  **Upload** the CSV below.
    3.  **Push** the 'Cleaned' version to your account to get ownership and full API access.
    """)

st.write("---")

# Path A: The "Easy Option" (CSV Upload)
st.subheader("📂 Option 1: Upload Exportify CSV")
uploaded_file = st.file_uploader("Drop Exportify CSV here", type=["csv"])

if uploaded_file:
    raw_filename = uploaded_file.name.rsplit('.', 1)[0]
    clean_p_name = re.sub(r'[^a-zA-Z0-9_]', '_', raw_filename)
    
    with st.spinner("Analyzing for duplicates..."):
        df_csv = process_exportify_csv(uploaded_file)
        
        # Track unique vs duplicate tracks
        unique_tracks = []
        all_dupes = []
        seen_ids = set()

        for idx, row in df_csv.iterrows():
            tid = row['Spotify-id']
            if tid not in seen_ids:
                unique_tracks.append(tid)
                seen_ids.add(tid)
            else:
                all_dupes.append(row.to_dict())
        
        if all_dupes:
            df_dupes = pd.DataFrame(all_dupes)
            df_dupes.insert(0, 'Pos', range(1, len(df_dupes) + 1))
            df_dupes['BPM'] = df_dupes['BPM'].astype(str)
            
            st.warning(f"Found {len(all_dupes)} duplicates in '{raw_filename}'.")
            st.dataframe(df_dupes, use_container_width=True, hide_index=True)
            
            # --- ACTION BUTTONS ---
            c1, c2 = st.columns(2)
            with c1:
                # Download the report
                safe_proj = st.session_state.get("global_proj", "Project")
                st.download_button(
                    label="📥 Download Duplicate Report",
                    data=df_dupes.to_csv(index=False).encode('utf-8'),
                    file_name=f"AfexCloud_{safe_proj}_{clean_p_name}_Duplicates.csv",
                    mime="text/csv"
                )
            
            with c2:
                # 2026 PUSH LOGIC
                if st.button("🚀 PUSH CLEANED PLAYLIST TO MY SPOTIFY"):
                    if not token_info:
                        st.error("Connect Spotify first.")
                    else:
                        try:
                            sp = spotipy.Spotify(auth_manager=auth_manager)
                            # Use 2026-compliant 'current_user' endpoint 
                            new_p_name = f"Cleaned - {raw_filename}"
                            new_p = sp.current_user_playlist_create(name=new_p_name, public=False)
                            
                            # Add unique tracks in batches 
                            uris = [t if t.startswith('spotify:track:') else f"spotify:track:{t}" for t in unique_tracks]
                            for i in range(0, len(uris), 100):
                                batch = uris[i:i+100]
                                sp._post(f"playlists/{new_p['id']}/items", payload={"uris": batch})
                            
                            st.success(f"Successfully created '{new_p_name}' on your account!")
                            st.balloons()
                        except Exception as e:
                            st.error(f"Push failed: {e}")
        else:
            st.success("No duplicates found! Your CSV data is already clean.")
