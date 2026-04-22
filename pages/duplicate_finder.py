import streamlit as st
import pandas as pd
import re
import unicodedata
from collections import defaultdict
from afexcloud.layout import bootstrap_page
import spotipy
# 2026 Wrapper Imports
from spotify_utils import get_playlist_data, get_track_info

# 1. Page Config
st.set_page_config(page_title="Duplicate Finder | AfexCloud", page_icon="🔍", layout="wide")

# 2. Bootstrap Style & Security
auth_manager, token_info = bootstrap_page()

# 3. Tool Helpers
def advanced_normalize(text):
    """Normalization logic to catch subtle duplicates."""
    if not isinstance(text, str): text = str(text)
    text = unicodedata.normalize('NFKD', text)
    text = "".join([c for c in text if not unicodedata.combining(c)])
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def get_playlist_metadata(url_or_id, sp):
    """Fetches track list using the authenticated user session."""
    p_id = url_or_id.split('/')[-1].split('?')[0] if '/' in url_or_id else url_or_id
    try:
        # Fetch playlist metadata
        meta = sp.playlist(p_id)
        p_name = meta['name']
        tracks = []
        
        # 2026 Wrapper: Find 'items' vs 'tracks'
        results = get_playlist_data(meta)
        
        while results:
            for item in results.get('items', []):
                # 2026 Wrapper: Handle 'track' vs 'item' rename
                t = get_track_info(item)
                if t:
                    tracks.append({
                        'Spotify-id': t.get('id'), 
                        'Name': t.get('name', 'Unknown'), 
                        'Artist': t['artists'][0]['name'] if t.get('artists') else 'Unknown', 
                        'Album': t['album']['name'] if t.get('album') else 'Unknown'
                    })
            
            # Support for long playlists (pagination)
            results = sp.next(results) if results.get('next') else None
            
        return p_name, tracks
    except Exception as e:
        st.error(f"Spotify API Error: {e}")
        return "Unknown", []

# 4. Tool Logic
st.title(f"🔍 Duplicate Finder")

if not token_info:
    st.warning("Connect Spotify first via the sidebar to scan your library.")
else:
    sp = spotipy.Spotify(auth_manager=auth_manager)
    url = st.text_input("Enter Playlist URL/ID to scan for duplicates:")

    if st.button("🚀 Run Duplicate Scan"):
        if not url:
            st.warning("Please provide a playlist URL first.")
        else:
            with st.spinner("Analyzing tracks..."):
                p_name, tracks = get_playlist_metadata(url, sp)
                
                if tracks:
                    # Group by Spotify ID
                    by_id = defaultdict(list)
                    for t in tracks:
                        if t['Spotify-id']:
                            by_id[t['Spotify-id']].append(t)
                    
                    dupes = [item for group in by_id.values() if len(group) > 1 for item in group]
                    
                    if dupes:
                        st.warning(f"Found {len(dupes)} duplicates in '{p_name}'.")
                        df_dupes = pd.DataFrame(dupes)
                        st.dataframe(df_dupes, use_container_width=True, hide_index=True)
                        
                        safe_proj = re.sub(r'[^a-zA-Z0-9_]', '_', st.session_state.get('global_proj', 'Default'))
                        f_name = f"{safe_proj}_Duplicates_{p_name.replace(' ', '_')}.csv"
                        
                        st.download_button(
                            "📥 Download Duplicate Report", 
                            df_dupes.to_csv(index=False).encode('utf-8'), 
                            f_name, 
                            "text/csv"
                        )
                    else:
                        st.success(f"No duplicates found in '{p_name}'! Your library is clean.")
                else:
                    st.info("No tracks found. (2026 Rule: You can only scan playlists you own).")
