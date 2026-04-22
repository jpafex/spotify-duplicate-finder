import streamlit as st
import pandas as pd
from afexcloud.layout import bootstrap_page
# Import the new wrappers
from spotify_utils import get_playlist_data, get_track_info 
import spotipy

bootstrap_page()

st.title("📋 Song Lister")
url = st.text_input("Enter Playlist URL/ID:")

if st.button("Generate Inventory"):
    # We now fetch directly to ensure 2026 compliance
    from afexcloud.spotify_auth import get_auth_manager
    auth_manager, _ = bootstrap_page()
    sp = spotipy.Spotify(auth_manager=auth_manager)
    
    try:
        # Extract ID from URL if necessary
        p_id = url.split('/')[-1].split('?')[0] if '/' in url else url
        results = sp.playlist(p_id)
        p_name = results['name']
        
        # Use wrapper to find 'items' vs 'tracks' in the playlist response
        items_list = get_playlist_data(results).get('items', [])
        
        parsed_tracks = []
        for idx, item in enumerate(items_list):
            # WRAPPER TIE-IN: Handle 'track' vs 'item' rename
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
            st.warning("No tracks found or playlist is restricted (2026 Rule: You must own the playlist).")
        else:
            df = pd.DataFrame(parsed_tracks)
            df['Playlist'] = p_name
            
            # Reorder columns for display
            cols = ['Original Pos', 'Name', 'Artist', 'Album', 'Playlist', 'Spotify-id']
            st.dataframe(df[cols], use_container_width=True, hide_index=True)

            # Download logic
            st.download_button(
                "📥 Download Inventory",
                df.to_csv(index=False).encode("utf-8"),
                f"inventory_{p_id}.csv",
                "text/csv",
            )
            
    except Exception as e:
        st.error(f"Spotify API Error: {e}. (Reminder: You must own the playlist in 2026 Development Mode).")
