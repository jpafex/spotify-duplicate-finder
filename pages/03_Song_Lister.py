import streamlit as st
import pandas as pd
import spotipy
from afexcloud.layout import bootstrap_page
# Import the 2026 wrappers from your new utility file
from spotify_utils import get_playlist_data, get_track_info 

# 1. Page Config & Bootstrap (Called ONLY once)
st.set_page_config(page_title="Song Lister | AfexCloud", page_icon="📋", layout="wide")
auth_manager, token_info = bootstrap_page()

# 2. Tool Logic
st.title("📋 Song Lister")

if not token_info:
    st.warning("Connect Spotify first via the sidebar to access your library.")
else:
    sp = spotipy.Spotify(auth_manager=auth_manager)
    url = st.text_input("Enter Playlist URL/ID:", placeholder="https://open.spotify.com/playlist/...")

    if st.button("Generate Inventory"):
        if not url:
            st.error("Please enter a valid Playlist URL or ID.")
        else:
            with st.spinner("Analyzing tracks..."):
                try:
                    # Extract ID from URL
                    p_id = url.split('/')[-1].split('?')[0] if '/' in url else url
                    
                    # Fetch playlist data
                    results = sp.playlist(p_id)
                    p_name = results['name']
                    
                    # 2026 Wrapper: Find 'items' vs 'tracks'
                    playlist_content = get_playlist_data(results)
                    items_list = playlist_content.get('items', [])
                    
                    parsed_tracks = []
                    for idx, item in enumerate(items_list):
                        # 2026 Wrapper: Handle 'track' vs 'item' rename
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
                        st.warning("No tracks found. (2026 Rule: New Development Mode accounts can only list tracks for playlists they own or collaborate on).")
                    else:
                        df = pd.DataFrame(parsed_tracks)
                        df['Playlist'] = p_name
                        
                        # Set column order for final display
                        final_cols = ['Original Pos', 'Name', 'Artist', 'Album', 'Playlist', 'Spotify-id']
                        st.dataframe(df[final_cols], use_container_width=True, hide_index=True)

                        # Download Logic
                        safe_proj = st.session_state.get("global_proj", "project")
                        csv_data = df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label="📥 Download Inventory",
                            data=csv_data,
                            file_name=f"{safe_proj}_song_list.csv",
                            mime="text/csv",
                        )
                        
                except Exception as e:
                    st.error(f"Spotify API Error: {e}")
