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

st.title("📈 Gap Mirror (Precision Acquisition)")

# WORKFLOW TOGGLE: Pro-active move for management
mode = st.radio(
    "Choose Workflow Mode:",
    ["🔍 Automated Gap Audit (Compare to Local)", "⚡ Manual Quick-Select (One-File Mode)"],
    horizontal=True,
    help="Use 'Automated' to check your library, or 'Manual' to build a quote from a single list."
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
        client_f = st.file_uploader("Upload Client CSV", type=["csv"], key="client_src", label_visibility="collapsed")
    with c2:
        st.subheader("2. Local Files (Mp3Tag File)")
        library_f = st.file_uploader("Upload Local Library CSV", type=["csv"], key="lib_src", label_visibility="collapsed")

    if client_f and library_f:
        try:
            with st.spinner("Analyzing library alignment..."):
                # Process Client Request
                df_client = process_exportify_csv(client_f)
                client_p_name_raw = client_f.name.rsplit('.', 1)[0]
                
                df_client["match_key"] = df_client.apply(
                    lambda r: f"{advanced_normalize(r['Name'])}__{advanced_normalize(r['Artist'])}__{advanced_normalize(r['Album'])}", 
                    axis=1
                )

                # Process Local Library
                df_lib = pd.read_csv(library_f)
                df_lib["match_key"] = df_lib.apply(
                    lambda r: f"{advanced_normalize(str(r.iloc[0]))}__{advanced_normalize(str(r.iloc[1]))}__{advanced_normalize(str(r.iloc[2]))}" 
                    if len(r) >= 3 else "", axis=1
                )
                local_keys = set(df_lib["match_key"].tolist())

                # Set initial flags
                df_client['Status'] = df_client['match_key'].apply(lambda x: "🚩 Missing" if x not in local_keys else "✅ Match")
                df_client['Acquire?'] = df_client['Status'] == "🚩 Missing"
                df_to_process = df_client
        except Exception as e:
            st.error(f"Audit failed: {e}")

# --- WORKFLOW 2: MANUAL QUICK-SELECT ---
else:
    st.subheader("🚀 Manual Acquisition Selection")
    st.caption("Upload a single Exportify file and manually pick songs for the acquisition quote.")
    manual_f = st.file_uploader("Upload Exportify CSV", type=["csv"], key="manual_src")
    
    if manual_f:
        try:
            df_manual = process_exportify_csv(manual_f)
            client_p_name_raw = manual_f.name.rsplit('.', 1)[0]
            
            # Defaults for Manual Mode
            df_manual['Status'] = "⚡ Manual"
            df_manual['Acquire?'] = False # Let management pick the songs
            df_to_process = df_manual
        except Exception as e:
            st.error(f"Ingestion failed: {e}")

# --- UNIFIED REVIEW & PUSH SECTION ---
if df_to_process is not None:
    st.write("---")
    st.subheader("📋 Acquisition & Quality Review")
    
    # Interaction Layer
    cols_to_show = ['Acquire?', 'Status', 'Name', 'Artist', 'Album', 'BPM', 'Spotify-id']
    edited_df = st.data_editor(
        df_to_process[cols_to_show],
        hide_index=True,
        use_container_width=True,
        column_config={
            "Acquire?": st.column_config.CheckboxColumn(help="Include in acquisition quote"),
            "Status": st.column_config.TextColumn(disabled=True),
            "Spotify-id": st.column_config.TextColumn(disabled=True)
        }
    )

    final_list = edited_df[edited_df['Acquire?'] == True].copy()
    
    # Metrics
    m1, m2 = st.columns(2)
    m1.metric("Tracks in Quote", len(final_list))
    if "Automated" in mode:
        m2.metric("Manual Upgrades", len(final_list[final_list['Status'] == "✅ Match"]))

    if not final_list.empty:
        st.write("---")
        st.subheader("🚀 Finalize and Push to Spotify")
        new_p_name = st.text_input("Acquisition Playlist Name:", value=f"Acquire - {client_p_name_raw}")
        
        if st.button("🔥 CREATE CLIENT REVIEW PLAYLIST"):
            if not token_info:
                st.error("Connect Spotify first via the sidebar.")
            else:
                try:
                    sp = spotipy.Spotify(auth_manager=auth_manager)
                    new_p = sp.current_user_playlist_create(name=new_p_name, public=True)
                    uris = [tid if str(tid).startswith('spotify:track:') else f"spotify:track:{tid}" 
                            for tid in final_list['Spotify-id'].dropna().tolist()]
                    
                    for i in range(0, len(uris), 100):
                        batch = uris[i:i+100]
                        sp._post(f"playlists/{new_p['id']}/items", payload={"uris": batch})
                    
                    st.success(f"Success! '{new_p_name}' created on your account.")
                    st.balloons()
                except Exception as e:
                    st.error(f"Push failed: {e}")

        # Final Export for Management
        st.download_button(
            label="📥 Download Acquisition Report (Excel Ready)",
            data=final_list.to_csv(index=False).encode('utf-8-sig'),
            file_name=f"Acquisition_Quote_{client_p_name_raw}.csv",
            mime="text/csv",
            use_container_width=True
        )
