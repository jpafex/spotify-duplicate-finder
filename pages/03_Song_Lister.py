import streamlit as st
import pandas as pd
import spotipy
from afexcloud.layout import bootstrap_page
# Import the new 2026-ready utilities
from spotify_utils import get_playlist_data, get_track_info, process_exportify_csv

# 1. Page Config
st.set_page_config(page_title="Song Lister | AfexCloud", page_icon="📋", layout="wide")

# 2. Bootstrap Style & Security
auth_manager, token_info = bootstrap_page()

# 3. Tool Logic
st.title("📋 Song Lister")
st.info("2026 Update: Use Exportify CSVs to view BPM and Popularity data restricted by the API.")

# Path A: The "Easy Option" (CSV Upload)
st.subheader("📂 Option 1: Upload Exportify CSV")
uploaded_file = st.file_uploader("Drop your Exportify CSV here to bypass API Ownership rules", type=["csv"])

if uploaded_file:
    with st.spinner("Processing CSV data..."):
        df_csv = process_exportify_csv(uploaded_file)
        st.success("Successfully loaded data from CSV.")
        
        # Display the result
        st.dataframe(df_csv, use_container_width=True, hide_index=True)
        
        # Download button for the processed version
        safe_proj = st.session_state.get("global_proj", "project")
        st.download_button(
            label="📥 Download Clean Inventory",
            data=df_csv.to_csv(index=False).encode('utf-8'),
            file_name=f"{safe_proj}_clean_list.csv",
            mime="text/csv"
        )

st.write("---")

# Path B: The "API Option" (URL Input)
st.subheader("🌐 Option 2: Spotify URL (API Path)")
if not token_info:
    st.warning("Connect Spotify via the sidebar to use the API path.")
else:
    sp = spotipy.Spotify(auth_manager=auth_manager)
    url = st.text_input("Enter Playlist URL/ID:")

    if st.button("Generate API Inventory"):
        if not url:
            st.error("Please enter a URL.")
        else:
            with st.spinner("Fetching from Spotify..."):
                try:
                    p_id = url.split('/')[-1].split('?')[0] if '/' in url else url
                    results = sp.playlist(p_id)
                    
                    # 2026 Wrapper: Find 'items' vs 'tracks' 
                    content = get_playlist_data(results)
                    items_list = content.get('items', [])
                    
                    parsed_tracks = []
                    for idx, item in enumerate(items_list):
                        # 2026 Wrapper: Handle 'track' vs 'item' 
                        t = get_track_info(item)
                        if t:
                            parsed_tracks.append({
                                "Original Pos": idx + 1,
                                "Name": t.get('name', 'Unknown'),
                                "Artist": ", ".join([a['name'] for a in t.get('artists', [])]),
                                "Album": t.get('album', {}).get('name', 'Unknown'),
                                "Spotify-id": t.get('id')
                            })
                    
                    if not parsed_tracks:
                        st.warning("No tracks found. (2026 Rule: API access is restricted for non-owned playlists).")
                    else:
                        df_api = pd.DataFrame(parsed_tracks)
                        st.dataframe(df_api, use_container_width=True, hide_index=True)
                        
                except Exception as e:
                    st.error(f"Spotify API Error: {e}")
