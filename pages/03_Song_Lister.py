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

# --- NEWBIE GUIDE & EXPORTIFY LINK ---
with st.expander("🆕 New here? How to get a CSV from Exportify", expanded=True):
    st.markdown("""
    Because of the **2026 Spotify API rules**, we use **Exportify** to get data (like BPM) that Spotify now hides.
    1.  **Open [Exportify.net](https://exportify.net/)** in a new tab.
    2.  **Log in** with your Spotify account.
    3.  Find the playlist you need to analyze.
    4.  Click the green **'Export'** button to download the CSV.
    5.  Drag and drop that CSV into **Option 1** below!
    """)
    st.link_button("🔗 Go to Exportify.net", "https://exportify.net/")

st.write("---")

# Path A: The "Easy Option" (CSV Upload)
st.subheader("📂 Option 1: Upload Exportify CSV")
uploaded_file = st.file_uploader("Drop Exportify CSV here to bypass 2026 Ownership rules", type=["csv"])

if uploaded_file:
    # Extract name for the dynamic download filename
    raw_filename = uploaded_file.name.rsplit('.', 1)[0]
    clean_p_name = re.sub(r'[^a-zA-Z0-9_]', '_', raw_filename)
    
    with st.spinner("Refining playlist data..."):
        df_csv = process_exportify_csv(uploaded_file)
        
        # Add line position numbers at the beginning
        df_csv.insert(0, 'Pos', range(1, len(df_csv) + 1))
        
        # DISPLAY FIX: Force BPM to a string to hide all decimals/trailing zeros
        df_csv['BPM'] = df_csv['BPM'].astype(str)
        
        st.success(f"Data Refined for: {raw_filename}")
        
        # Display the formatted DataFrame
        st.dataframe(df_csv, use_container_width=True, hide_index=True)
        
        # DYNAMIC FILENAME DOWNLOAD
        safe_proj = st.session_state.get("global_proj", "Project")
        timestamp = datetime.now().strftime("%Y%m%d")
        
        st.download_button(
            label=f"📥 Download Cleaned {raw_filename} Inventory",
            data=df_csv.to_csv(index=False).encode('utf-8'),
            file_name=f"AfexCloud_{safe_proj}_{clean_p_name}_Cleaned_{timestamp}.csv",
            mime="text/csv"
        )

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
                api_p_name = re.sub(r'[^a-zA-Z0-9_]', '_', results['name'])
                
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
                    
                    safe_proj = st.session_state.get("global_proj", "Project")
                    st.download_button(
                        label="📥 Download Cleaned Playlist Inventory",
                        data=df_api.to_csv(index=False).encode('utf-8'),
                        file_name=f"AfexCloud_{safe_proj}_{api_p_name}_API_Cleaned.csv",
                        mime="text/csv"
                    )
                        
            except Exception as e:
                st.error(f"Spotify API Error: {e}")
