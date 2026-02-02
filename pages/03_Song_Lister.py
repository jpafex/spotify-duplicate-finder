import streamlit as st
import pandas as pd
from afexcloud.layout import bootstrap_page
from afexcloud.utils import get_playlist_metadata

bootstrap_page()

st.title("📋 Song Lister")
url = st.text_input("Enter Playlist URL/ID:")

if st.button("Generate Inventory"):
    p_name, tracks = get_playlist_metadata(
        url_or_id=url,
        client_id=st.secrets["SPOTIFY_CLIENT_ID"],
        client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"],
    )
    if not tracks:
        st.warning("No tracks found (check playlist ID/URL).")
    else:
        # Create DataFrame from tracks
        df = pd.DataFrame(tracks)
        
        # Add playlist name column
        df['Playlist'] = p_name
        
        # Reorder columns: move Spotify-id to the end, add Playlist before it
        # Keep Original Pos, Name, Artist, Album as first columns
        column_order = ['Original Pos', 'Name', 'Artist', 'Album']
        
        # Get remaining columns (excluding the ones we've already ordered and the ones we'll move to the end)
        remaining_columns = [col for col in df.columns 
                           if col not in column_order and 
                           col not in ['Spotify-id', 'Playlist']]
        
        # Create final column order
        final_column_order = column_order + remaining_columns + ['Playlist', 'Spotify-id']
        
        # Reorder the DataFrame
        df = df[final_column_order]
        
        # Display the DataFrame
        st.dataframe(df, use_container_width=True, hide_index=True)

        safe_proj = st.session_state.get("_safe_proj", "project")
        st.download_button(
            "📥 Download Inventory",
            df.to_csv(index=False).encode("utf-8"),
            f"{safe_proj}_inventory.csv",
            "text/csv",
        )
