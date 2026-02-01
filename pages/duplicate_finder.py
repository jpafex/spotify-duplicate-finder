import streamlit as st
import pandas as pd
import re
import unicodedata
from collections import defaultdict
from afexcloud.layout import bootstrap_page
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials

# 1. Page Config (Must be the first Streamlit command on the page)
st.set_page_config(page_title="Duplicate Finder | AfexCloud", page_icon="🔍", layout="wide")

# 2. Bootstrap the AfexCloud Look and Security
auth_manager, token_info = bootstrap_page()

# 3. Local Tool Helpers
def advanced_normalize(text):
    """Normalization logic to catch subtle duplicates."""
    if not isinstance(text, str): text = str(text)
    try: text = text.encode('cp1252').decode('utf-8')
    except: pass
    text = unicodedata.normalize('NFKD', text)
    text = "".join([c for c in text if not unicodedata.combining(c)])
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def get_playlist_metadata(url_or_id):
    """Fetches track list for duplicate analysis."""
    sp_read = Spotify(auth_manager=SpotifyClientCredentials(
        client_id=st.secrets["SPOTIFY_CLIENT_ID"],
        client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"]
    ))
    p_id = url_or_id.split('/')[-1].split('?')[0] if '/' in url_or_id else url_or_id
    try:
        meta = sp_read.playlist(p_id, fields="name")
        p_name = meta['name']
        tracks = []
        results = sp_read.playlist_tracks(p_id)
        while results:
            for item in results['items']:
                if item.get('track'):
                    t = item['track']
                    tracks.append({
                        'Spotify - id': t.get('id'), 
                        'Name': t.get('name', 'Unknown'), 
                        'Artist': t['artists'][0]['name'] if t.get('artists') else 'Unknown', 
                        'Album': t['album']['name'] if t.get('album') else 'Unknown'
                    })
            results = sp_read.next(results) if results['next'] else None
        return p_name, tracks
    except Exception as e:
        st.error(f"Spotify API Error: {e}")
        return "Unknown", []

# 4. Tool Logic
st.title(f"🔍 Duplicate Finder")
if st.session_state.get('global_proj'):
    st.caption(f"Active Project: {st.session_state['global_proj']}")

url = st.text_input("Enter Playlist URL/ID to scan for duplicates:")

if st.button("🚀 Run Duplicate Scan"):
    if not url:
        st.warning("Please provide a playlist URL first.")
    else:
        with st.spinner("Analyzing tracks..."):
            p_name, tracks = get_playlist_metadata(url)
            
            if tracks:
                # Group by Spotify ID
                by_id = defaultdict(list)
                for t in tracks:
                    by_id[t['Spotify - id']].append(t)
                
                # Identify entries with the same ID occurring more than once
                dupes = [item for group in by_id.values() if len(group) > 1 for item in group]
                
                if dupes:
                    st.warning(f"Found {len(dupes)} duplicates in '{p_name}'.")
                    df_dupes = pd.DataFrame(dupes)
                    st.dataframe(df_dupes, use_container_width=True, hide_index=True)
                    
                    # File naming based on project
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
