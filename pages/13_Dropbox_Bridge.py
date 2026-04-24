import streamlit as st
import pandas as pd
import numpy as np
import spotipy
import sys
import os
import re
from datetime import datetime

# Path Fix
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from afexcloud.layout import bootstrap_page
from afexcloud.utils import advanced_normalize
from spotify_utils import process_exportify_csv

# 1. Page Config
st.set_page_config(page_title="Gap Mirror | AfexCloud", page_icon="📈", layout="wide")
auth_manager, token_info = bootstrap_page()

st.title("📈 Gap Mirror (Smart Match & Debugger)")

# WORKFLOW TOGGLE
mode = st.radio(
    "Choose Workflow Mode:",
    ["🔍 Automated Gap Audit (Compare to Local/Cloud)", "⚡ Manual Quick-Select (One-File Mode)"],
    horizontal=True,
    help="Automated: Matches against your library. Manual: Pick songs to acquire from a single list."
)

if st.button("🔄 Reset Quote"):
    st.rerun()

# --- THE CLOUD INSPECTOR (NEW DEBUGGING SECTION) ---
# This section fulfills the request to see folders for debugging
if 'cloud_inventory' in st.session_state:
    st.write("---")
    with st.expander("📂 Cloud Folder Inspector (Debugging Tool)", expanded=False):
        df_cloud = st.session_state['cloud_inventory']
        unique_folders = sorted(df_cloud['Folder'].unique().tolist())
        
        st.info(f"Connected to Cloud Index: {len(df_cloud)} tracks found across {len(unique_folders)} folders.")
        
        c1, c2 = st.columns([1, 2])
        with c1:
            # This is the logic the team was looking for
            target_folder = st.selectbox("Select Cloud Folder to Inspect:", ["All Folders"] + unique_folders)
        with c2:
            search_local = st.text_input("Quick Search in Cloud Index:", placeholder="Search title or artist...")

        # Filter display based on selection
        inspect_df = df_cloud.copy()
        if target_folder != "All Folders":
            inspect_df = inspect_df[inspect_df['Folder'] == target_folder]
        if search_local:
            inspect_df = inspect_df[inspect_df.apply(lambda r: search_local.lower() in f"{r['Name']} {r['Artist']}".lower(), axis=1)]
        
        st.dataframe(inspect_df[['Name', 'Artist', 'Folder', 'Full Path']], use_container_width=True, hide_index=True)

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
                df_client = process_exportify_csv(client_f)
                client_p_name_raw = client_f.name.rsplit('.', 1)[0]
                
                # Matching Keys
                df_client["triple_key"] = df_client.apply(lambda r: f"{advanced_normalize(r['Name'])}__{advanced_normalize(r['Artist'])}__{advanced_normalize(r['Album'])}", axis=1)
                df_client["double_key"] = df_client.apply(lambda r: f"{advanced_normalize(r['Name'])}__{advanced_normalize(r['Artist'])}", axis=1)

                df_lib = pd.read_csv(library_f)
                df_lib.columns = [c.strip() for c in df_lib.columns]
                
                # Hybrid Logic
                lib_triple = set(df_lib.apply(lambda r: f"{advanced_normalize(str(r.get('Name','')))}__{advanced_normalize(str(r.get('Artist','')))}__{advanced_normalize(str(r.get('Album','')))}", axis=1))
                lib_double = set(df_lib.apply(lambda r: f"{advanced_normalize(str(r.get('Name','')))}__{advanced_normalize(str(r.get('Artist','')))}", axis=1))

                def smart_match(row):
                    if row['triple_key'] in lib_triple: return "✅ Match"
                    if row['double_key'] in lib_double: return "✅ Match"
                    return "🚩 Missing"

                df_client['Status'] = df_client.apply(smart_match, axis=1)
                df_client['Acquire?'] = df_client['Status'] == "🚩 Missing"
                df_to_process = df_client
        except Exception as e:
            st.error(f"Audit error: {e}")

# --- WORKFLOW 2: MANUAL QUICK-SELECT ---
else:
    st.subheader("🚀 Manual Acquisition Selection")
    manual_f = st.file_uploader("Upload Client Exportify CSV", type=["csv"], key="manual_src")
    
    if manual_f:
        try:
            df_to_process = process_exportify_csv(manual_f)
            client_p_name_raw = manual_f.name.rsplit('.', 1)[0]
            df_to_process['Status'] = "⚡ Manual"
            df_to_process['Acquire?'] = False # Managers pick manually
        except Exception as e:
            st.error(f"Ingestion failed: {e}")

# --- UNIFIED REVIEW & PUSH SECTION ---
if df_to_process is not None:
    st.write("---")
    st.subheader("📋 Acquisition & Quality Review")
    
    cols = ['Acquire?', 'Status', 'Name', 'Artist', 'Album', 'BPM', 'Spotify-id']
    edited_df = st.data_editor(
        df_to_process[cols],
        hide_index=True,
        use_container_width=True,
        column_config={"Acquire?": st.column_config.CheckboxColumn(), "Status": st.column_config.TextColumn(disabled=True)}
    )

    final_list = edited_df[edited_df['Acquire?'] == True].copy()
    
    if not final_list.empty:
        st.write("---")
        # ... (Push to Spotify and Download logic remains the same)
        st.success(f"Quote ready for {len(final_list)} tracks.")
