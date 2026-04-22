def get_track_obj(item_obj):
    """
    Safely retrieves the track/song object from a playlist item.
    In 2026, 'track' was renamed to 'item' in playlist responses.
    """
    # 1. 2026 Rule: 'track' is now 'item'
    if 'item' in item_obj:
        return item_obj['item']
    
    # 2. Legacy Rule: Use 'track'
    if 'track' in item_obj:
        return item_obj['track']
        
    # 3. Fallback: If the object is already the track (e.g. from Search)
    return item_obj

def get_playlist_data(playlist_obj):
    """ (Existing function from our last step) """
    if 'items' in playlist_obj: return playlist_obj['items']
    if 'tracks' in playlist_obj: return playlist_obj['tracks']
    return {"total": 0, "items": []}
