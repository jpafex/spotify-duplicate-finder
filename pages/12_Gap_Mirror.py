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
st.info("Automated Gap Analysis with Manual Quality Override for library upgrades.")

if st.button("🔄 Reset Current Session"):
    st.rerun()

# --- STEP 1: UPLOAD DATA ---
c1, c2 = st.columns(2)
with c1:
    st.subheader("1. Client Request (Exportify File)")
    st.caption("Upload the ground-truth list from the client's Spotify.")
    client_f = st.file_uploader("Upload Client CSV", type=["csv"], key="client_src", label_visibility="collapsed")
with c2:
    st.subheader("2. Local Files (Mp3Tag File)")
    st.caption("Upload your current local inventory for comparison.")
    library_f = st.file_uploader("Upload Local Library CSV", type=["csv"], key="lib_src", label_visibility="collapsed")

if client_f and library_f:
    try:
        with st.spinner("Analyzing library alignment..."):
            # A. Process Client Request
            df_client = process_exportify_csv(client_f)
            df_client["match_key"] = df_client.apply(
                lambda r: f"{advanced_normalize(r['Name'])}__{advanced_normalize(r['Artist'])}__{advanced_normalize(r['Album'])}", 
                axis=1
            )

            # B. Process Local Library
            df_lib = pd.read_csv(library_f)
            df_lib["match_key"] = df_lib.apply(
                lambda r: f"{advanced_normalize(str(r.iloc[0]))}__{advanced_normalize(str(r.iloc[1]))}__{advanced_normalize(str(r.iloc[2]))}" 
                if len(r) >= 3 else "", axis=1
            )
            local_keys = set(df_lib["match_key"].tolist())

            # C. THE HYBRID LOGIC
            # Initial Flagging
            df_client['Status'] = df_client['match_key'].apply(lambda x: "🚩 Missing" if x not in local_keys else "✅ Match")
            
            # Initial Acquisition Setting: Pre-select Missing songs for acquisition
            df_client['Acquire?'] = df_client['Status'] == "🚩 Missing"

            # D. THE INTERACTIVE QUOTE EDITOR
            st.write("---")
            st.subheader("📋 Acquisition & Quality Review")
            st.markdown("""
            **Team Instructions:** - Songs marked **🚩 Missing** are pre-selected for acquisition.
            - If a **✅ Match** is low quality (e.g., 128kbps), **check the 'Acquire?' box** to add it to the quote.
            """)

            # Filter columns for the editor
            cols_to_show = ['Acquire?', 'Status', 'Name', 'Artist', 'Album', 'BPM', 'Spotify-id']
            
            # The Data Editor allows the 'Manual Override'
            edited_df = st.data_editor(
                df_client[cols_to_show],
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Acquire?": st.column_config.CheckboxColumn(help="Select to include in acquisition quote"),
                    "Status": st.column_config.TextColumn(disabled=True),
                    "Spotify-id": st.column_config.TextColumn(disabled=True)
                }
            )

            # E. CALCULATE THE FINAL QUOTE
            final_acquisition_list = edited_df[edited_df['Acquire?'] == True].copy()
            
            st.write("---")
            q1, q2 = st.columns(2)
            q1.metric("Tracks in Final Quote", len(final_acquisition_list))
            q2.metric("Manual Upgrades Identified", len(final_acquisition_list[final_acquisition_list['Status'] == "✅ Match"]), delta_color="normal")

            if not final_acquisition_list.empty:
                # F. PUSH THE CUSTOM LIST TO SPOTIFY
                st.subheader("🚀 Step 3: Push Selection to Client Review")
                client_p_name_raw = client_f.name.rsplit('.', 1)[0]
                new_p_name = st.text_input("Review Playlist Name:", value=f"Acquisition Quote - {client_p_name_raw}")
                
                if st.button("🔥 CREATE CUSTOM REVIEW PLAYLIST"):
                    if not token_info:
                        st.error("Connect Spotify first.")
                    else:
                        sp = spotipy.Spotify(auth_manager=auth_manager)
                        # Create new playlist
                        new_p = sp.current_user_playlist_create(name=new_p_name, public=True)
                        p_id = new_p['id']
                        
                        # Prepare URIs for the verified acquisition list
                        uris = [tid if str(tid).startswith('spotify:track:') else f"spotify:track:{tid}" 
                                for tid in final_acquisition_list['Spotify-id'].dropna().tolist()]
                        
                        # Batch Push
                        for i in range(0, len(uris), 100):
                            batch = uris[i:i+100]
                            sp._post(f"playlists/{p_id}/items", payload={"uris": batch})
                        
                        st.success(f"Playlist created with {len(uris)} tracks for client review!")
                        st.balloons()
                
                # G. DOWNLOAD THE PROFESSIONAL QUOTE
                st.download_button(
                    label="📥 Download Acquisition Quote (CSV for Management)",
                    data=final_acquisition_list.to_csv(index=False).encode('utf-8-sig'),
                    file_name=f"Acquisition_Quote_{client_p_name_raw}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.info("No songs selected for acquisition.")

    except Exception as e:
        st.error(f"Gap Analysis error: {e}")
