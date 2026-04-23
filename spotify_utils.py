import pandas as pd
import numpy as np

def get_playlist_data(playlist_obj):
    """Safely retrieves playlist metadata across 2026 and legacy versions."""
    if 'items' in playlist_obj:
        return playlist_obj['items']
    if 'tracks' in playlist_obj:
        return playlist_obj['tracks']
    return {"total": 0, "items": []}

def get_track_info(item_obj):
    """Handles the 2026 'track' to 'item' field rename."""
    if 'item' in item_obj:
        return item_obj['item']
    if 'track' in item_obj:
        return item_obj['track']
    return item_obj

def process_exportify_csv(uploaded_file):
    """
    Parses Exportify CSV and strips BPM decimals.
    Recovers data (BPM, Pop) redacted by the 2026 API.
    """
    df = pd.read_csv(uploaded_file)
    
    # Mapping Exportify headers
    df_mapped = df.rename(columns={
        'Track Name': 'Name',
        'Artist Name(s)': 'Artist',
        'Album Name': 'Album',
        'Track URI': 'Spotify-id',
        'Tempo': 'BPM',
        'Popularity': 'Pop'
    })
    
    # FORCED BPM CLEANING: Use floor conversion to remove decimals (e.g., 134.964 -> 134)
    # This prevents Streamlit from "helpfully" re-adding decimals in the UI.
    df_mapped['BPM'] = pd.to_numeric(df_mapped['BPM'], errors='coerce').fillna(0).apply(np.floor).astype(int)
    
    # Ensure required columns exist
    required_cols = ['Name', 'Artist', 'Album', 'BPM', 'Pop', 'Spotify-id']
    for col in required_cols:
        if col not in df_mapped.columns:
            df_mapped[col] = "N/A"
            
    return df_mapped[required_cols]

def process_exportify_csv_trimmed(uploaded_file):
    """
    Trims Exportify data to the Core Four: Pos, Name, Artist, Album.
    Standardizes headers for the Collection Reviewer.
    """
    df = pd.read_csv(uploaded_file)
    
    # Mapping Exportify headers
    df_mapped = df.rename(columns={
        'Track Name': 'Name',
        'Artist Name(s)': 'Artist',
        'Album Name': 'Album',
        'Track URI': 'Spotify-id'
    })
    
    # Add the Original Pos (1, 2, 3...)
    df_mapped.insert(0, 'Pos', range(1, len(df_mapped) + 1))
    
    # Trim to requested columns only
    cols_to_keep = ['Pos', 'Name', 'Artist', 'Album']
    # Ensure they exist (fallback to empty string if missing)
    for col in cols_to_keep:
        if col not in df_mapped.columns:
            df_mapped[col] = ""
            
    return df_mapped[cols_to_keep]
