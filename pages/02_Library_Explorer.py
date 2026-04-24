import streamlit as st
import pandas as pd
import spotipy
import sys
import os
import re

# Path Fix for 'pages' folder access
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from afexcloud.layout import bootstrap_page

# 1. Page Config
st.set_page_config(page_title="Library Explorer | AfexCloud", page_icon="📂", layout="wide")
auth_manager, token_info = bootstrap_page()

st.title("📂 Library Explorer & Bulk Intake")

# --- KAIZEN WISH: THE BULK FOLLOWER ---
with st.expander("➕ Bulk Follower (Intake Station)", expanded=False):
    st.markdown("Paste multiple Spotify Playlist URLs (one per line) to add them to your library instantly.")
    bulk_input = st.text_area("Playlist URLs:", placeholder="https://open.spotify.com/playlist/...\nhttps://open.spotify.com/playlist/...", height=150)
    
    if st.button("🚀 Bulk Follow All"):
        if not token_info:
            st.error("Connect Spotify via the sidebar first.")
        else:
            sp = spotipy.Spotify(auth_manager=auth_manager)
            urls = [u.strip() for u in bulk_input.split('\n') if u.strip()]
            success_count = 0
            
            for url in urls:
                try:
                    # Extract ID from various URL formats
                    p_id = url.split('/')[-1].split('?')[0] if '/' in url else url
                    # 2026 Rule: Following public playlists is a permitted 'Write' action
                    sp.current_user_follow_playlist(p_id)
                    success_count += 1
                except Exception as e:
                    st.error(f"Failed to follow: {url} - {e}")
            
            if success_count > 0:
                st.success(f"Successfully followed {success_count} playlists! Click 'Refresh' below to see them.")
                st.balloons()

st.write("---")

# 2. THE LIBRARY EXPLORER
if st.button("🔄 Refresh & Audit My Library"):
    st.rerun()

if not token_info:
    st.warning("Please connect Spotify via the sidebar to scan your library.")
else:
    try:
        sp = spotipy.Spotify(auth_manager=auth_manager)
        
        with st.spinner("Inventorying your library..."):
            # Fetching 2026-compliant user playlist data
            results = sp.current_user_playlists(limit=50)
            playlists = []
            
            while results:
                for p in results['items']:
                    playlists.append({
                        "Name": p['name'],
                        "Tracks": p['tracks']['total'],
                        "ID": p['id'],
                        "Owner": p['owner']['display_name'],
                        "Is_Owner": p['owner']['id'] == sp.current_user()['id']
                    })
                results = sp.next(results) if results['next'] else None
            
            if not playlists:
                st.info("No playlists found. Use the Bulk Follower above to add client lists.")
            else:
                df = pd.DataFrame(playlists)
                
                # --- DASHBOARD METRICS ---
                c1, c2 = st.columns(2)
                c1.metric("Total Playlists", len(df))
                c2.metric("Owned by You", len(df[df['Is_Owner'] == True]))

                st.write("---")
                
                # --- THE AUDIT LIST ---
                for idx, row in df.iterrows():
                    border_color = "blue" if row['Is_Owner'] else "orange"
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.write(f"### {row['Name']}")
                            status = "🏠 Owned" if row['Is_Owner'] else "🔗 Following"
                            st.caption(f"{status} | {row['Tracks']} tracks | Owner: {row['Owner']}")
                        
                        with col2:
                            # Direct bridge to unlock the data
                            st.link_button("📂 Export CSV", f"https://exportify.net/app#/playlists/{row['ID']}")
                        
                        with col3:
                            # Quick link to preview in Spotify
                            st.link_button("🎧 Open App", f"https://api.spotify.com/v1/users/1210284965/playlists?limit=50{row['ID']}")

    except Exception as e:
        st.error(f"Library audit failed: {e}")
