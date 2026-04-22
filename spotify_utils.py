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
    Parses Exportify CSV and cleans BPM formatting for AfexCloud standards.
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
    
    # NEW: BPM Formatting - Remove decimals and trailing numbers
    # Converts 134.964 to 134
    df_mapped['BPM'] = pd.to_numeric(df_mapped['BPM'], errors='coerce').fillna(0).astype(int)
    
    # Ensure required columns exist
    required_cols = ['Name', 'Artist', 'Album', 'BPM', 'Pop', 'Spotify-id']
    for col in required_cols:
        if col not in df_mapped.columns:
            df_mapped[col] = "N/A"
            
    return df_mapped[required_cols]
