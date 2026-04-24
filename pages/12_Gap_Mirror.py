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

st.title("📈 Gap Mirror (Smart Auditor)")

mode = st.radio("Mode:", ["🔍 Automated Gap Audit", "⚡ Manual Quick-Select"], horizontal=True)

if st.button("🔄 Reset Auditor"):
    st.rerun()

df_to_process = None
client_p_name_raw = "New_Project"

if "Automated" in mode:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("1. Client Request")
        client_f = st.file_uploader("Upload Client CSV", type=["csv"], key="client_src")
    with c2:
        st.subheader("2. Inventory")
        library_f = st.file_uploader("Upload Dropbox Audit CSV", type=["csv"], key="lib_src")

    if client_f and library_f:
        try:
            with st.spinner("Analyzing Concatenated Triple-Match..."):
                # A. Process Client Request
                df_client = process_exportify_csv(client_f)
                client_p_name_raw = client_f.name.rsplit('.', 1)[0]
                
                # B. Process Inventory with BOM Removal
                df_lib = pd.read_csv(library_f, encoding='utf-8')
                df_lib.columns = [c.strip().replace('\ufeff', '') for c in df_lib.columns]

                # Ensure matching logic handles Spotify's Chilenas.csv headers
                # 'process_exportify_csv' usually gives us Name, Artist, Album
                
                # C. BUILD KEYS (Ignoring Album for the fallback match)
                lib_triple = set(df_lib.apply(lambda r: f"{advanced_normalize(str(r.get('Name','')))}|{advanced_normalize(str(r.get('Artist','')))}|{advanced_normalize(str(r.get('Album','')))}", axis=1))
                lib_double = set(df_lib.apply(lambda r: f"{advanced_normalize(str(r.get('Name','')))}|{advanced_normalize(str(r.get('Artist','')))}", axis=1))

                def audit_logic(row):
                    n, a, alb = advanced_normalize(row['Name']), advanced_normalize(row['Artist']), advanced_normalize(row['Album'])
                    triple = f"{n}|{a}|{alb}"
                    double = f"{n}|{a}"
                    
                    if triple in lib_triple: return "✅ Triple Match"
                    if double in lib_double: return "✅ Match (Name/Artist)"
                    return "🚩 Missing"

                df_client['Status'] = df_client.apply(audit_logic, axis=1)
                df_client['Acquire?'] = df_client['Status'] == "🚩 Missing"
                df_to_process = df_client

                if st.checkbox("🐞 Debug: Show Key Pairs"):
                    st.write("Lib Example:", list(lib_double)[0] if lib_double else "None")
                    st.write("Client Example:", f"{advanced_normalize(df_client['Name'].iloc[0])}|{advanced_normalize(df_client['Artist'].iloc[0])}")

        except Exception as e:
            st.error(f"Audit failed: {e}")

# --- MANUAL MODE & PUSH ---
# ... (Standard manual and push logic should be pasted below)
elif "Manual" in mode:
    st.subheader("🚀 Manual Selection")
    manual_f = st.file_uploader("Upload CSV", type=["csv"], key="manual_src")
    if manual_f:
        df_to_process = process_exportify_csv(manual_f)
        df_to_process['Status'] = "⚡ Manual"
        df_to_process['Acquire?'] = False

if df_to_process is not None:
    st.write("---")
    edited_df = st.data_editor(df_to_process[['Acquire?','Status','Name','Artist','Album']], hide_index=True, use_container_width=True)
    if st.button("🔥 PUSH MISSING TO SPOTIFY"):
        # ... (Push logic from turn 10 goes here)
        pass
