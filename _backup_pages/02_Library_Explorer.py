import streamlit as st
import pandas as pd
import spotipy
import sys
import os
import re

# Path Fix
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from afexcloud.layout import bootstrap_page

# 1. Page Config
st.set_page_config(page_title="Library Explorer | AfexCloud", page_icon="📂", layout="wide")
auth_manager, token_info = bootstrap_page()

st.title("📂 Library Explorer")

# RESET BUTTON (Kaizen Request)
if st.button("🔄 Refresh Library View"):
    st.rerun()

st.info("2026 Compliant: Scanning YOUR library for owned and followed playlists.")

if not token_info:
    st.warning("Please connect Spotify via the sidebar to scan your library.")
else:
    try:
        sp = spotipy.Spotify(auth_manager=auth_manager)
        
        with st.spinner("Fetching your playlists..."):
            # 2026 Rule: Use 'current_user_playlists' to stay inside the Ownership Wall
            results = sp.current_user_playlists(limit=50)
            playlists = []
            
            while results:
                for p in results['items']:
                    # KAIZEN FIX: Use .get() to prevent crashes on non-standard playlists
                    tracks_info = p.get('tracks', {})
                    owner_info = p.get('owner', {})
                    
                    playlists.append({
                        "Name": p.get('name', 'Unnamed Playlist'),
                        "Tracks": tracks_info.get('total', 0),
                        "ID": p.get('id'),
                        "Owner": owner_info.get('display_name', 'Unknown'),
                        "Is_Owner": owner_info.get('id') == sp.current_user()['id']
                    })
                results = sp.next(results) if results['next'] else None
            
            if not playlists:
                st.warning("No playlists found in your library.")
            else:
                df = pd.DataFrame(playlists)
                
                # --- DASHBOARD METRICS ---
                c1, c2 = st.columns(2)
                c1.metric("Total Playlists", len(df))
                c2.metric("Owned by You", len(df[df['Is_Owner'] == True]))

                st.write("---")
                
                # --- INTERACTIVE LIST ---
                for idx, row in df.iterrows():
                    # Color coding for newbies: Blue for owned, Orange for followed
                    border_color = "blue" if row['Is_Owner'] else "orange"
                    
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.write(f"### {row['Name']}")
                            status = "🏠 Owned" if row['Is_Owner'] else "🔗 Following"
                            st.caption(f"{status} | {row['Tracks']} tracks | Owner: {row['Owner']}")
                        
                        with col2:
                            # The 'Maze-Buster' bridge to Exportify
                            st.link_button("📂 Export CSV", f"https://exportify.net/app#/playlists/{row['ID']}")
                        
                        with col3:
                            # Direct link to open in Spotify App
                            st.link_button("🎧 Open App", f"https://open.spotify.com/user/1210284965?si=2bf05c8463944b1f{row['ID']}")

    except Exception as e:
        st.error(f"Library scan failed: {e}")
