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
        
        # DEBUGGING: Show what columns we actually have
        st.write(f"Debug: Available columns in tracks data: {list(df.columns)}")
        
        # Add playlist name column
        df['Playlist'] = p_name
        
        # Define base columns that should come first
        base_columns = ['Original Pos', 'Name', 'Artist', 'Album']
        
        # Get all columns from the DataFrame
        all_columns = list(df.columns)
        
        # Remove base columns and special columns from the list
        special_columns = ['Spotify-id', 'Playlist']
        columns_to_reorder = [col for col in all_columns 
                            if col not in base_columns and col not in special_columns]
        
        # Build the final column order
        final_columns = []
        
        # Add base columns that actually exist
        for col in base_columns:
            if col in df.columns:
                final_columns.append(col)
        
        # Add other columns
        final_columns.extend(columns_to_reorder)
        
        # Add Playlist and Spotify-id at the end
        if 'Playlist' in df.columns:
            final_columns.append('Playlist')
        
        if 'Spotify-id' in df.columns:
            final_columns.append('Spotify-id')
        
        # Only reorder if we have columns
        if final_columns:
            df = df[final_columns]
        
        # Display the DataFrame
        st.dataframe(df, use_container_width=True, hide_index=True)

        safe_proj = st.session_state.get("_safe_proj", "project")
        st.download_button(
            "📥 Download Inventory",
            df.to_csv(index=False).encode("utf-8"),
            f"{safe_proj}_inventory.csv",
            "text/csv",
        )
