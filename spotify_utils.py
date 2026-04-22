def get_playlist_data(playlist_obj, field="items"):
    """
    Safely retrieves playlist metadata (tracks/items) across 
    2026 and legacy Spotify API versions.
    """
    # 1. New 2026 Rule: 'tracks' renamed to 'items'
    if 'items' in playlist_obj:
        return playlist_obj['items']
    
    # 2. Legacy/Grandfathered Rule: Use 'tracks'
    if 'tracks' in playlist_obj:
        return playlist_obj['tracks']
        
    # 3. Security/Restriction Rule: Return empty structure if field is blocked
    # This prevents 'KeyError' on restricted non-owned playlists.
    return {"total": 0, "href": ""}
