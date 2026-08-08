import streamlit as st
import pandas as pd
import spotipy
import sys
import os
import re
from datetime import datetime

# Path Fix for 'pages' folder access
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from afexcloud.layout import bootstrap_page
from spotify_utils import get_playlist_data, get_track_info, process_exportify_csv

# 1. Page Config
st.set_page_config(page_title="Song Lister | AfexCloud", page_icon="📋", layout="wide")

# 2. Bootstrap Style & Security
auth_manager, token_info = bootstrap_page()

# 3. Tool Logic
st.title("📋 Song Lister")

# Newbie Guide for Mirroring
with st.expander("🆕 Mirroring Guide", expanded=False):
    st.markdown("""
    1. **Obtain Playlist** Copy Client Playlist link, if you click on playlist link, will open in 
    Spotify. When Playlist is displayed in your account, since you don't own the playlist, 
    Use the 3 dots ... in Spotify, or Spotify menu, look for "Add to Your Library." Once added proceed to next step.
    2. **Export** any client playlist via [Exportify.net](https://exportify.net/). Once in Exportify.net webpage, you
    will see all the playlist that you own, only the one's you own display. Select the playlist to export for CSV file.
    3. **Upload** the CSV below to see BPM and assign Position numbers.
    4. **Mirror**: Click the push button to create a copy on your own account for full API access.
    """)

st.write("---")

# Path A: The "Easy Option" (CSV Upload)
st.subheader("📂 Option 1: Upload Exportify CSV")
uploaded_file = st.file_uploader("Drop Exportify CSV here to bypass 2026 Ownership rules", type=["csv"])

if uploaded_file:
    # Extract playlist name for dynamic usage
    raw_filename = uploaded_file.name.rsplit('.', 1)[0]
    clean_p_name = re.sub(r'[^a-zA-Z0-9_]', '_', raw_filename)
    
    with st.spinner("Refining playlist data..."):
        # standardizing headers and rounding BPM
        df_csv = process_exportify_csv(uploaded_file)
        
        # Add line position numbers (1, 2, 3...)
        df_csv.insert(0, 'Pos', range(1, len(df_csv) + 1))
        
        # Display fix for BPM decimals
        df_csv['BPM'] = df_csv['BPM'].astype(str)
        
        st.success(f"Data Refined for: {raw_filename}")
        
        # Display the formatted DataFrame
        st.dataframe(df_csv, use_container_width=True, hide_index=True)
        
        # Action Row: Download and Mirror
        c1, c2 = st.columns(2)
        
        with c1:
            safe_proj = st.session_state.get("global_proj", "Project")
            timestamp = datetime.now().strftime("%Y%m%d")
            st.download_button(
                label=f"📥 Download Cleaned {raw_filename} Inventory",
                data=df_csv.to_csv(index=False).encode('utf-8-sig'),
                file_name=f"AfexCloud_{safe_proj}_{clean_p_name}_Cleaned_{timestamp}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
        with c2:
            st.write("---")
            st.subheader("🚀 Mirror to My Spotify")
            mirror_name = st.text_input("New Playlist Name:", value=f"Mirror - {raw_filename}")
            
            if st.button("🔥 PUSH MIRROR TO MY ACCOUNT"):
                if not token_info:
                    st.error("Connect Spotify first via the sidebar.")
                else:
                    try:
                        sp = spotipy.Spotify(auth_manager=auth_manager)
                        
                        # 2026 Rule: Must use current_user_playlist_create (POST /me/playlists)
                        new_p = sp.current_user_playlist_create(name=mirror_name, public=False)
                        p_id = new_p['id']
                        
                        # Prepare Track URIs from CSV
                        uris = [tid if str(tid).startswith('spotify:track:') else f"spotify:track:{tid}" 
                                for tid in df_csv['Spotify-id'].dropna().tolist()]
                        
                        # Add items in 2026-compliant batches of 100
                        for i in range(0, len(uris), 100):
                            batch = uris[i:i+100]
                            # Targeting the new /items endpoint suffix
                            sp._post(f"playlists/{p_id}/items", payload={"uris": batch})
                        
                        st.success(f"Successfully mirrored '{mirror_name}' with {len(uris)} tracks!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Mirroring failed: {e}")

st.write("---")

# Path B: The "API Option" (URL Input - Still subject to Ownership Wall)
st.subheader("🌐 Option 2: Spotify URL (API Path)")
if not token_info:
    st.warning("Connect Spotify via the sidebar to use the API path.")
else:
    sp = spotipy.Spotify(auth_manager=auth_manager)
    url = st.text_input("Enter Playlist URL/ID:")

    if st.button("Generate API Inventory"):
        with st.spinner("Fetching from Spotify..."):
            try:
                p_id = url.split('/')[-1].split('?')[0] if '/' in url else url
                results = sp.playlist(p_id)
                
                content = get_playlist_data(results)
                items_list = content.get('items', [])
                
                parsed_tracks = []
                for idx, item in enumerate(items_list):
                    t = get_track_info(item)
                    if t:
                        parsed_tracks.append({
                            "Pos": idx + 1,
                            "Name": t.get('name', 'Unknown'),
                            "Artist": ", ".join([a['name'] for a in t.get('artists', [])]),
                            "Album": t.get('album', {}).get('name', 'Unknown'),
                            "Spotify-id": t.get('id')
                        })
                
                if not parsed_tracks:
                    st.warning("No tracks found. (2026 Rule: API restricted for non-owned playlists).")
                else:
                    df_api = pd.DataFrame(parsed_tracks)
                    st.dataframe(df_api, use_container_width=True, hide_index=True)
                        
            except Exception as e:
                st.error(f"Spotify API Error: {e}")
