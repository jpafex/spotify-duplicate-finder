import pandas as pd

def get_playlist_data(playlist_obj):
    """
    Safely retrieves playlist metadata (tracks/items) across 
    2026 and legacy Spotify API versions.
    """
    if 'items' in playlist_obj:
        return playlist_obj['items']
    if 'tracks' in playlist_obj:
        return playlist_obj['tracks']
    return {"total": 0, "items": []}

def get_track_info(item_obj):
    """
    Safely extracts the track object from a playlist item.
    In 2026, 'track' was renamed to 'item' for new Client IDs.
    """
    if 'item' in item_obj:
        return item_obj['item']
    if 'track' in item_obj:
        return item_obj['track']
    return item_obj

def process_exportify_csv(uploaded_file):
    """
    Parses the Exportify CSV to bypass 2026 API redactions.
    Returns a clean DataFrame with data like BPM and Popularity.
    """
    df = pd.read_csv(uploaded_file)
    
    # Mapping Exportify headers to AfexCloud standard
    # This recovers the BPM (Tempo) data the 2026 API now hides.
    df_mapped = df.rename(columns={
        'Track Name': 'Name',
        'Artist Name(s)': 'Artist',
        'Album Name': 'Album',
        'Track URI': 'Spotify-id',
        'Tempo': 'BPM',
        'Popularity': 'Pop'
    })
    
    # Ensure columns exist even if the CSV format changes
    required_cols = ['Name', 'Artist', 'Album', 'BPM', 'Pop', 'Spotify-id']
    for col in required_cols:
        if col not in df_mapped.columns:
            df_mapped[col] = "N/A"
            
    return df_mapped[required_cols]
