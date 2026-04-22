import streamlit as st
import pandas as pd
import sys
import os
import re
from datetime import datetime

# Path Fix for 'pages' folder access
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from afexcloud.layout import bootstrap_page
from afexcloud.utils import advanced_normalize
# Import the maze-buster utilities
from spotify_utils import process_exportify_csv

# 1. Page Config
st.set_page_config(page_title="Library Auditor | AfexCloud", page_icon="💿", layout="wide")

# 2. Bootstrap Style & Security
auth_manager, token_info = bootstrap_page()

# 3. Tool Logic
st.title("💿 Library Auditor")

# --- NEWBIE GUIDE & EXPORTIFY LINK ---
with st.expander("🆕 New here? How to audit client playlists", expanded=True):
    st.markdown("""
    Spotify's **2026 rules** prevent the API from reading playlists you don't own. 
    1.  **Export the client's playlist** as a CSV using [Exportify.net](https://exportify.net/).
    2.  **Upload that CSV** as your 'Spotify Inventory' below.
    3.  **Upload your Local Songs CSV** to see what's missing from your mp3 collection.
    """)
    st.link_button("🔗 Go to Exportify.net", "https://exportify.net/")

st.write("---")

c1, c2 = st.columns(2)
with c1:
    st.subheader("1. Spotify Inventory")
    inv_f = st.file_uploader("Upload Exportify CSV or Afex Cleaned CSV", type="csv")
with c2:
    st.subheader("2. Local Collection")
    loc_f = st.file_uploader("Upload Local Songs CSV", type="csv")

if inv_f and loc_f:
    if st.button("🔍 Run Library Audit"):
        with st.spinner("Comparing libraries..."):
            # Process Spotify Inventory (Handles Exportify or Afex formats)
            try:
                # We use process_exportify_csv to ensure standard headers
                df_inv = process_exportify_csv(inv_f)
            except:
                # Fallback if it's already an Afex-cleaned CSV
                df_inv = pd.read_csv(inv_f)

            df_loc = pd.read_csv(loc_f)

            # Create comparison keys for matching
            # Format: 'songname__artistname' normalized for accuracy
            df_inv["compare_key"] = df_inv.apply(
                lambda r: f"{advanced_normalize(str(r['Name']))}__{advanced_normalize(str(r['Artist']))}", axis=1
            )
            
            # Local keys (Assumes first column is 'Song,Artist' or similar format)
            loc_keys = {
                f"{advanced_normalize(str(e).split(',')[0])}__{advanced_normalize(str(e).split(',')[1])}"
                for e in df_loc.iloc[:, 0]
                if len(str(e).split(",")) >= 2
            }

            # Identify Missing Tracks
            missing_df = df_inv[~df_inv["compare_key"].isin(loc_keys)].copy()
            
            # Display Results
            st.metric("Missing Tracks", len(missing_df))
            
            if not missing_df.empty:
                st.warning("The following tracks are in the Spotify playlist but missing from your local library.")
                
                # Cleaning BPM for display before showing table
                if 'BPM' in missing_df.columns:
                    missing_df['BPM'] = pd.to_numeric(missing_df['BPM'], errors='coerce').fillna(0).astype(int).astype(str)
                
                # Show key columns
                display_cols = ["Name", "Artist", "Album", "BPM"] if "BPM" in missing_df.columns else ["Name", "Artist", "Album"]
                st.dataframe(missing_df[display_cols], use_container_width=True, hide_index=True)

                # DYNAMIC FILENAME DOWNLOAD
                safe_proj = st.session_state.get("global_proj", "Project")
                p_name_raw = inv_f.name.rsplit('.', 1)[0]
                clean_p_name = re.sub(r'[^a-zA-Z0-9_]', '_', p_name_raw)
                timestamp = datetime.now().strftime("%Y%m%d")

                st.download_button(
                    label=f"📥 Download Missing Tracks Report ({p_name_raw})",
                    data=missing_df[display_cols].to_csv(index=False).encode("utf-8"),
                    file_name=f"AfexCloud_{safe_proj}_{clean_p_name}_Missing_Report_{timestamp}.csv",
                    mime="text/csv",
                )
            else:
                st.success("Audit Complete: Your local library contains all songs in this playlist!")
