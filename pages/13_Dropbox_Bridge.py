import streamlit as st
import pandas as pd
import numpy as np
import spotipy
import sys
import os
import re
from datetime import datetime

# Path Fix for 'pages' folder access
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from afexcloud.layout import bootstrap_page
from afexcloud.utils import advanced_normalize
from spotify_utils import process_exportify_csv

# 1. Page Config
st.set_page_config(page_title="Gap Mirror | AfexCloud", page_icon="📈", layout="wide")
auth_manager, token_info = bootstrap_page()

st.title("📈 Gap Mirror (Smart Match Edition)")

# WORKFLOW TOGGLE
mode = st.radio(
    "Choose Workflow Mode:",
    ["🔍 Automated Gap Audit (Compare to Local/Cloud)", "⚡ Manual Quick-Select (One-File Mode)"],
    horizontal=True
)

if st.button("🔄 Reset Quote"):
    st.rerun()

df_to_process = None
client_p_name_raw = "New_Project"

# --- WORKFLOW 1: AUTOMATED AUDIT ---
if "Automated" in mode:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("1. Client Request (Exportify File)")
        client_f = st.file_uploader("Upload Client CSV", type=["csv"], key="client_src")
    with c2:
        st.subheader("2. Inventory (Mp3Tag or Dropbox Bridge)")
        library_f = st.file_uploader("Upload Inventory CSV", type=["csv"], key="lib_src")

    if client_f and library_f:
        try:
            with st.spinner("Executing Smart Match..."):
                # A. Process Client Request
                df_client = process_exportify_csv(client_f)
                client_p_name_raw = client_f.name.rsplit('.', 1)[0]
                
                # Create Primary Key (Triple) and Secondary Key (Double)
                df_client["triple_key"] = df_client.apply(
                    lambda r: f"{advanced_normalize(r['Name'])}__{advanced_normalize(r['Artist'])}__{advanced_normalize(r['Album'])}", axis=1)
                df_client["double_key"] = df_client.apply(
                    lambda r: f"{advanced_normalize(r['Name'])}__{advanced_normalize(r['Artist'])}", axis=1)

                # B. Process Inventory
                df_lib = pd.read_csv(library_f)
                
                # Normalize inventory columns to handle both Dropbox and MP3Tag formats
                df_lib.columns = [c.strip() for c in df_lib.columns]
                lib_mapping = {'Name': 'Name', 'Artist': 'Artist', 'Album': 'Album'}
                df_lib = df_lib.rename(columns={k: v for k, v in lib_mapping.items() if k in df_lib.columns})

                # Generate matching sets for speed
                lib_triple_keys = set(df_lib.apply(
                    lambda r: f"{advanced_normalize(str(r.get('Name','')))}__{advanced_normalize(str(r.get('Artist','')))}__{advanced_normalize(str(r.get('Album','')))}", axis=1))
                lib_double_keys = set(df_lib.apply(
                    lambda r: f"{advanced_normalize(str(r.get('Name','')))}__{advanced_normalize(str(r.get('Artist','')))}", axis=1))

                # C. THE SMART MATCH (Kaizen Fix)
                def perform_smart_match(row):
                    if row['triple_key'] in lib_triple_keys:
                        return "✅ Match"
                    elif row['double_key'] in lib_double_keys:
                        # Success! Found via name + artist fallback
                        return "✅ Match"
                    return "🚩 Missing"

                df_client['Status'] = df_client.apply(perform_smart_match, axis=1)
                df_client['Acquire?'] = df_client['Status'] == "🚩 Missing"
                df_to_process = df_client
                
        except Exception as e:
            st.error(f"Smart Match failed: {e}")

# --- WORKFLOW 2: MANUAL QUICK-SELECT (Omitted for brevity, remains the same) ---
else:
    # ... (Manual mode remains as previously written)
    pass

# --- UNIFIED REVIEW & PUSH SECTION ---
if df_to_process is not None:
    st.write("---")
    st.subheader("📋 Acquisition & Quality Review")
    
    cols_to_show = ['Acquire?', 'Status', 'Name', 'Artist', 'Album', 'BPM', 'Spotify-id']
    edited_df = st.data_editor(
        df_to_process[cols_to_show],
        hide_index=True,
        use_container_width=True,
        column_config={
            "Acquire?": st.column_config.CheckboxColumn(help="Select to acquire"),
            "Status": st.column_config.TextColumn(disabled=True)
        }
    )

    final_list = edited_df[edited_df['Acquire?'] == True].copy()
    
    # ... (Metrics and Push logic remains the same)
    st.write(f"### Current Result: {len(final_list)} tracks marked for acquisition.")
