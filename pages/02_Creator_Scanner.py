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
st.set_page_config(page_title="Creator Scanner | AfexCloud", page_icon="👤", layout="wide")
auth_manager, token_info = bootstrap_page()

st.title("👤 Creator Scanner")
st.info("Input a public Spotify profile to audit and export their playlists.")

creator_url = st.text_input("Enter Creator URL or ID:", placeholder="e.g., https://open.spotify.com/user/jpefex")

if st.button("🔍 Scan Public Profile"):
    if not token_info:
        st.error("Connect Spotify first via the sidebar.")
    elif not creator_url:
        st.warning("Please provide a User URL or ID.")
    else:
        try:
            sp = spotipy.Spotify(auth_manager=auth_manager)
            
            # Extract User ID from URL
            u_id = creator_url.split('/')[-1].split('?')[0] if '/' in creator_url else creator_url
            
            with st.spinner(f"Scanning playlists for {u_id}..."):
                # Fetching public playlists for the target user
                results = sp.user_playlists(u_id)
                playlists = []
                
                while results:
                    for p in results['items']:
                        playlists.append({
                            "Name": p['name'],
                            "Tracks": p['tracks']['total'],
                            "ID": p['id'],
                            "Owner": p['owner']['display_name']
                        })
                    results = sp.next(results) if results['next'] else None
                
                if not playlists:
                    st.warning("No public playlists found for this creator profile.")
                else:
                    st.success(f"Discovered {len(playlists)} public playlists.")
                    
                    # Create a clean display with individual export bridges
                    for p in playlists:
                        with st.container(border=True):
                            c1, c2 = st.columns([3, 1])
                            with c1:
                                st.write(f"### {p['Name']}")
                                st.caption(f"Tracks: {p['Tracks']} | Owner: {p['Owner']}")
                            with c2:
                                # Direct Exportify Bridge to bypass 2026 redactions
                                st.link_button("📂 Exportify CSV", f"https://exportify.net/app#/playlists/{p['ID']}")
                            
        except Exception as e:
            st.error(f"Profile scan failed: {e}. (Private profiles or 2026 restrictions may apply).")
