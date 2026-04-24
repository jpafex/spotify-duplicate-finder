import streamlit as st
import pandas as pd
import numpy as np
import spotipy
import sys
import os
import re
from datetime import datetime

# Path Fix for AfexCloud architecture
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from afexcloud.layout import bootstrap_page
from afexcloud.utils import advanced_normalize
from spotify_utils import process_exportify_csv

# 1. Page Config
st.set_page_config(page_title="Gap Mirror | AfexCloud", page_icon="📈", layout="wide")
auth_manager, token_info = bootstrap_page()

st.title("📈 Gap Mirror (100% Match Edition)")

# --- AGGRESSIVE NORMALIZATION ENGINE ---
def advanced_normalize_v2(text):
    """KAIZEN: Strips apostrophes, parentheses, and non-alphanumerics."""
    if not isinstance(text, str): return ""
    text = text.lower()
    # Remove apostrophes (The Los Player's Fix)
    text = text.replace("'", "").replace("’", "").replace("`", "")
    # Remove everything in parentheses (The Volveré/Tornero Fix)
    text = re.sub(r'\(.*?\)', '', text)
    # Strip everything except letters and numbers
    return re.sub(r'[^a-z0-9]', '', text).strip()

# --- WORKFLOW TOGGLE ---
mode = st.radio(
    "Select Workflow Mode:",
    ["🔍 Automated Gap Audit (Compare Library)", "⚡ Manual Quick-Select (One-File Mode)"],
    horizontal=True
)

if st.button("🔄 Reset Auditor"):
    st.rerun()

# --- THE CLOUD INSPECTOR (DEBUGGER) ---
if 'cloud_inventory' in st.session_state:
    st.write("---")
    with st.expander("📂 Cloud Folder Inspector (Debugging)", expanded=False):
        df_cloud = st.session_state['cloud_inventory']
        unique_folders = sorted(df_cloud['Folder'].unique().tolist())
        
        c1, c2 = st.columns([1, 2])
        with c1:
            target_folder = st.selectbox("Cloud Folder:", ["All Folders"] + unique_folders)
        with c2:
            search_local = st.text_input("Local Search:", placeholder="Verify Artist or Title in Cloud...")

        inspect_df = df_cloud.copy()
        if target_folder != "All Folders":
            inspect_df = inspect_df[inspect_df['Folder'] == target_folder]
        if search_local:
            inspect_df = inspect_df[inspect_df.apply(lambda r: search_local.lower() in f"{r['Name']} {r['Artist']}".lower(), axis=1)]
        
        st.dataframe(inspect_df[['Name', 'Artist', 'Album', 'Full Path']], use_container_width=True, hide_index=True)

df_to_process = None
client_p_name_raw = "New_Project"

# --- WORKFLOW 1: AUTOMATED AUDIT ---
if "Automated" in mode:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("1. Client Request (Spotify CSV)")
        client_f = st.file_uploader("Upload Client CSV", type=["csv"], key="client_src")
    with c2:
        st.subheader("2. Inventory (Dropbox CSV)")
        library_f = st.file_uploader("Upload Dropbox Audit CSV", type=["csv"], key="lib_src")

    if client_f and library_f:
        try:
            with st.spinner("Executing Surgical Audit..."):
                # A. Process Client Request
                df_client = process_exportify_csv(client_f)
                client_p_name_raw = client_f.name.rsplit('.', 1)[0]
                
                # B. Process Inventory with BOM Removal
                df_lib = pd.read_csv(library_f, encoding='utf-8')
                df_lib.columns = [c.strip().replace('\ufeff', '') for c in df_lib.columns]

                # C. BUILD KEYS (Triple & Double Fallback)
                # Library Keys
                lib_triple = set(df_lib.apply(lambda r: f"{advanced_normalize_v2(str(r.get('Name','')))}|{advanced_normalize_v2(str(r.get('Artist','')))}|{advanced_normalize_v2(str(r.get('Album','')))}", axis=1))
                lib_double = set(df_lib.apply(lambda r: f"{advanced_normalize_v2(str(r.get('Name','')))}|{advanced_normalize_v2(str(r.get('Artist','')))}", axis=1))

                def audit_logic(row):
                    n = advanced_normalize_v2(row['Name'])
                    a_full = advanced_normalize_v2(row['Artist'])
                    alb = advanced_normalize_v2(row['Album'])
                    
                    # KAIZEN: Multi-Artist Handling (The DKDAZ Fix)
                    a_first = advanced_normalize_v2(row['Artist'].split(';')[0].split(',')[0])
                    
                    triple = f"{n}|{a_full}|{alb}"
                    double_full = f"{n}|{a_full}"
                    double_first = f"{n}|{a_first}"
                    
                    if triple in lib_triple: return "✅ Triple Match"
                    if double_full in lib_double: return "✅ Match (Name/Artist)"
                    if double_first in lib_double: return "✅ Match (First Artist)"
                    return "🚩 Missing"

                df_client['Status'] = df_client.apply(audit_logic, axis=1)
                df_client['Acquire?'] = df_client['Status'] == "🚩 Missing"
                df_to_process = df_client

                if st.checkbox("🐞 Show Debug Keys"):
                    st.write("Lib Sample Key:", list(lib_double)[0] if lib_double else "None")
                    st.write("Client Sample Key:", f"{advanced_normalize_v2(df_client['Name'].iloc[0])}|{advanced_normalize_v2(df_client['Artist'].iloc[0])}")

        except Exception as e:
            st.error(f"Audit Error: {e}")

# --- WORKFLOW 2: MANUAL QUICK-SELECT ---
else:
    st.subheader("🚀 Manual Acquisition Selection")
    manual_f = st.file_uploader("Upload Spotify Exportify CSV", type=["csv"], key="manual_src")
    if manual_f:
        try:
            df_to_process = process_exportify_csv(manual_f)
            client_p_name_raw = manual_f.name.rsplit('.', 1)[0]
            df_to_process['Status'] = "⚡ Manual"
            df_to_process['Acquire?'] = False
        except Exception as e:
            st.error(f"Ingestion failed: {e}")

# --- UNIFIED REVIEW & PUSH SECTION ---
if df_to_process is not None:
    st.write("---")
    st.subheader("📋 Acquisition & Quality Review")
    
    # Selection Metrics
    m1, m2 = st.columns(2)
    m1.metric("Acquisitions Identified", len(df_to_process[df_to_process['Acquire?'] == True]))
    m2.metric("Library Matches", len(df_to_process[df_to_process['Acquire?'] == False]), delta_color="normal")

    cols = ['Acquire?', 'Status', 'Name', 'Artist', 'Album', 'BPM', 'Spotify-id']
    edited_df = st.data_editor(
        df_to_process[cols],
        hide_index=True,
        use_container_width=True,
        column_config={
            "Acquire?": st.column_config.CheckboxColumn(help="Select to add to acquisition quote"),
            "Status": st.column_config.TextColumn(disabled=True)
        }
    )

    final_list = edited_df[edited_df['Acquire?'] == True].copy()
    
    if not final_list.empty:
        st.write("---")
        st.subheader("🚀 Step 3: Push Selection to Spotify")
        new_p_name = st.text_input("Review Playlist Name:", value=f"Acquire - {client_p_name_raw}")
        
        if st.button("🔥 CREATE CLIENT REVIEW PLAYLIST"):
            if not token_info:
                st.error("Connect Spotify in the sidebar.")
            else:
                try:
                    sp = spotipy.Spotify(auth_manager=auth_manager)
                    new_p = sp.current_user_playlist_create(name=new_p_name, public=True)
                    uris = [tid if str(tid).startswith('spotify:track:') else f"spotify:track:{tid}" 
                            for tid in final_list['Spotify-id'].dropna().tolist()]
                    
                    for i in range(0, len(uris), 100):
                        batch = uris[i:i+100]
                        sp._post(f"playlists/{new_p['id']}/items", payload={"uris": batch})
                    
                    st.success(f"Playlist created with {len(final_list)} tracks!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Push failed: {e}")

        st.download_button(
            label="📥 Download Acquisition Quote (Excel Ready)",
            data=final_list.to_csv(index=False).encode('utf-8-sig'),
            file_name=f"Acquisition_Quote_{client_p_name_raw}.csv",
            mime="text/csv",
            use_container_width=True
        )
