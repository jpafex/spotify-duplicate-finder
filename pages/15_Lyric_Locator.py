import streamlit as st
import pandas as pd
import lyricsgenius
import re
import sys
import os
import requests # Added for header management
from datetime import datetime
from afexcloud.layout import bootstrap_page

# Path Fix
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from afexcloud.utils import advanced_normalize

# 1. Page Config
st.set_page_config(page_title="Lyric Locator | AfexCloud", page_icon="🎤", layout="wide")
bootstrap_page()

st.title("🎤 Lyric Locator (Stealth Edition)")
st.caption("High-Octane Performance | Cloudflare Bypass Enabled")

# 2. Aggressive Normalization
def locator_normalize(text):
    if not isinstance(text, str): return ""
    text = text.lower()
    text = text.replace("'", "").replace("’", "").replace("`", "")
    text = re.sub(r'\(.*?\)', '', text)
    return re.sub(r'[^a-z0-9]', '', text).strip()

# 3. Initialize Stealth Genius Engine
try:
    token = st.secrets["genius"]["access_token"]
    
    # KAIZEN: Custom Session with Browser Headers to bypass 403
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    })
    
    genius = lyricsgenius.Genius(token, session=session)
    genius.verbose = False 
    genius.remove_section_headers = True
    # We set skip_non_songs to True to avoid scraping noise
    genius.skip_non_songs = True 
except Exception as e:
    st.error(f"Genius Config Error: {e}")
    st.stop()

if 'nightly_requests' not in st.session_state:
    st.session_state['nightly_requests'] = []

# --- INTERFACE ---
st.write("---")
lyric_input = st.text_area("🎤 Type Lyrics / Snippets Here:", height=120, placeholder="Example: 'I've been inclined to believe they never would'")
search_btn = st.button("🔥 EXECUTE STEALTH SEARCH", use_container_width=True)

# --- SEARCH LOGIC ---
if search_btn and lyric_input:
    if 'cloud_inventory' not in st.session_state:
        st.error("🚨 **Inventory Empty**: Run a scan in 'Dropbox Bridge' first!")
    else:
        with st.spinner("Bypassing Security & Decoding Lyrics..."):
            try:
                # KAIZEN: Use search_songs (plural) for a more direct API hit
                # This often avoids the 403 triggered by scraping the full lyrics page
                search_results = genius.search_songs(lyric_input)
                
                if search_results and 'hits' in search_results:
                    # Get the top hit
                    top_hit = search_results['hits'][0]['result']
                    song_title = top_hit['title']
                    song_artist = top_hit['primary_artist']['name']
                    art_url = top_hit['song_art_image_thumbnail_url']
                    
                    st.success(f"🎯 **Identified**: '{song_title}' by **{song_artist}**")
                    st.image(art_url, width=150)
                    
                    # Match against the 45k index
                    df = st.session_state['cloud_inventory']
                    n_target = locator_normalize(song_title)
                    a_target = locator_normalize(song_artist.split()[0])
                    
                    match_df = df[
                        (df['Name'].apply(locator_normalize).str.contains(n_target, na=False)) & 
                        (df['Artist'].apply(locator_normalize).str.contains(a_target, na=False))
                    ]
                    
                    if not match_df.empty:
                        res = match_df.iloc[0]
                        st.balloons()
                        st.warning(f"📍 **Located in Folder**: `{res['Album']}`")
                        st.code(f"PATH: {res['Full Path']}", language="bash")
                        
                        if st.button("🚩 LOG AS ACTIVE REQUEST"):
                            st.session_state['nightly_requests'].append({
                                "Time": datetime.now().strftime("%H:%M:%S"),
                                "Song": res['Name'], "Artist": res['Artist'], "Location": res['Album']
                            })
                            st.toast(f"Request Logged: {res['Name']}")
                    else:
                        st.error("🚩 Song found in global database, but missing from your 2TB library.")
                else:
                    st.error("No matches found. Try more specific lyrics.")
            except Exception as e:
                # Detailed error for debugging the ivory tower
                st.error(f"Search Error: {e}")

# --- LOG DISPLAY ---
if st.session_state['nightly_requests']:
    st.write("---")
    st.subheader("📋 Session Request Log")
    st.dataframe(pd.DataFrame(st.session_state['nightly_requests']), use_container_width=True, hide_index=True)
