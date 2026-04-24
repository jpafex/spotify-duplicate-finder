import streamlit as st
import pandas as pd
import numpy as np
import spotipy
import sys
import os
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from afexcloud.layout import bootstrap_page
from afexcloud.utils import advanced_normalize
from spotify_utils import process_exportify_csv

st.set_page_config(page_title="Gap Mirror | AfexCloud", page_icon="📈", layout="wide")
auth_manager, token_info = bootstrap_page()

st.title("📈 Gap Mirror (100% Audit Edition)")

# 100% Normalization
def advanced_normalize_v2(text):
    if not isinstance(text, str): return ""
    text = text.lower()
    text = text.replace("'", "").replace("’", "").replace("`", "")
    text = re.sub(r'\(.*?\)', '', text)
    return re.sub(r'[^a-z0-9]', '', text).strip()

mode = st.radio("Workflow:", ["🔍 Automated Gap Audit", "⚡ Manual Quick-Select"], horizontal=True)

# --- CLOUD INSPECTOR (FIXED KEYERROR) ---
if 'cloud_inventory' in st.session_state:
    st.write("---")
    with st.expander("📂 Cloud Folder Inspector", expanded=False):
        df_cloud = st.session_state['cloud_inventory']
        # FIX: Using 'Album' because that's where the folder name lives now
        unique_folders = sorted(df_cloud['Album'].unique().tolist())
        
        target_folder = st.selectbox("Select Cloud Folder:", ["All Folders"] + unique_folders)
        search_local = st.text_input("Quick Search:")

        inspect_df = df_cloud.copy()
        if target_folder != "All Folders":
            inspect_df = inspect_df[inspect_df['Album'] == target_folder]
        if search_local:
            inspect_df = inspect_df[inspect_df.apply(lambda r: search_local.lower() in f"{r['Name']} {r['Artist']}".lower(), axis=1)]
        st.dataframe(inspect_df, use_container_width=True, hide_index=True)

df_to_process = None

if "Automated" in mode:
    c1, c2 = st.columns(2)
    with c1: client_f = st.file_uploader("Upload Client CSV", type=["csv"])
    with c2: library_f = st.file_uploader("Upload Inventory CSV", type=["csv"])

    if client_f and library_f:
        try:
            df_client = process_exportify_csv(client_f)
            df_lib = pd.read_csv(library_f, encoding='utf-8')
            df_lib.columns = [c.strip().replace('\ufeff', '') for c in df_lib.columns]

            # PREP KEYS
            lib_triple = set(df_lib.apply(lambda r: f"{advanced_normalize_v2(str(r.get('Name','')))}|{advanced_normalize_v2(str(r.get('Artist','')))}|{advanced_normalize_v2(str(r.get('Album','')))}", axis=1))
            lib_double = set(df_lib.apply(lambda r: f"{advanced_normalize_v2(str(r.get('Name','')))}|{advanced_normalize_v2(str(r.get('Artist','')))}", axis=1))

            def audit_logic(row):
                n, a_full, alb = advanced_normalize_v2(row['Name']), advanced_normalize_v2(row['Artist']), advanced_normalize_v2(row['Album'])
                # DKDAZ Fix: Match on first artist only
                a_first = advanced_normalize_v2(row['Artist'].split(';')[0].split(',')[0])
                
                if f"{n}|{a_full}|{alb}" in lib_triple: return "✅ Triple Match"
                if f"{n}|{a_full}" in lib_double: return "✅ Match (Name/Artist)"
                if f"{n}|{a_first}" in lib_double: return "✅ Match (First Artist)"
                return "🚩 Missing"

            df_client['Status'] = df_client.apply(audit_logic, axis=1)
            df_client['Acquire?'] = df_client['Status'] == "🚩 Missing"
            df_to_process = df_client
        except Exception as e: st.error(f"Audit failed: {e}")

if df_to_process is not None:
    st.write("---")
    edited_df = st.data_editor(df_to_process[['Acquire?','Status','Name','Artist','Album','BPM','Spotify-id']], hide_index=True, use_container_width=True)
    # ... (Download logic from before)
