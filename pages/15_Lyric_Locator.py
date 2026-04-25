import streamlit as st
import pandas as pd
import lyricsgenius
import re
import sys
import os
from datetime import datetime
from afexcloud.layout import bootstrap_page

# Path Fix
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from afexcloud.utils import advanced_normalize

# 1. Page Config
st.set_page_config(page_title="Lyric Locator | AfexCloud", page_icon="🎤", layout="wide")
bootstrap_page()

st.title("🎤 Lyric Locator & Request Center")
st.caption("Performance Search | Digital Request Log | Optimized for Evans/Greeley HQ")

# 2. Aggressive Normalization
def locator_normalize(text):
    if not isinstance(text, str): return ""
    text = text.lower()
    text = text.replace("'", "").replace("’", "").replace("`", "")
    text = re.sub(r'\(.*?\)', '', text)
    return re.sub(r'[^a-z0-9]', '', text).strip()

# 3. Initialize Genius
try:
    genius = lyricsgenius.Genius(st.secrets["genius"]["access_token"])
    genius.verbose = False 
except Exception:
    st.error("Genius API Token missing in secrets.toml!")
    st.stop()

# 4. Request Log Session State
if 'nightly_requests' not in st.session_state:
    st.session_state['nightly_requests'] = []

# --- PERFORMANCE INTERFACE ---
st.write("---")
c1, c2 = st.columns([2, 1])

with c1:
    lyric_q = st.text_area("🎤 Type Lyrics / Snippets Here:", height=120, placeholder="Example: 'Good times never seemed so good'")
    search_btn = st.button("🔥 EXECUTE DEEP SEARCH", use_container_width=True)

with c2:
    st.info("💡 **Greeley Pro-Tip**: Stuck on a title? Just type the hook. The engine does the rest.")

# --- SEARCH LOGIC ---
if search_btn and lyric_q:
    if 'cloud_inventory' not in st.session_state:
        st.error("🚨 **Inventory Empty**: Go to 'Dropbox Bridge' and run a scan first!")
    else:
        with st.spinner("Decoding Lyrics..."):
            try:
                song = genius.search_song(lyric_q)
                if song:
                    st.success(f"🎯 **Identified**: '{song.title}' by {song.artist}")
                    
                    # Match against the 45k index
                    df = st.session_state['cloud_inventory']
                    n_target = locator_normalize(song.title)
                    a_target = locator_normalize(song.artist.split()[0])
                    
                    match_df = df[
                        (df['Name'].apply(locator_normalize).str.contains(n_target, na=False)) & 
                        (df['Artist'].apply(locator_normalize).str.contains(a_target, na=False))
                    ]
                    
                    if not match_df.empty:
                        res = match_df.iloc[0]
                        st.balloons()
                        
                        # Display GPS Info
                        st.warning(f"📍 **Located in Folder**: `{res['Album']}`")
                        st.code(f"PATH: {res['Full Path']}", language="bash")
                        
                        # --- THE FLAG BUTTON ---
                        if st.button("🚩 LOG AS ACTIVE REQUEST", use_container_width=True):
                            st.session_state['nightly_requests'].append({
                                "Time": datetime.now().strftime("%H:%M:%S"),
                                "Song": res['Name'],
                                "Artist": res['Artist'],
                                "Location": res['Album']
                            })
                            st.toast(f"Request Logged: {res['Name']}")
                    else:
                        st.error("🚩 Song found in database, but missing from your 2TB library.")
                else:
                    st.error("No lyric matches found.")
            except Exception as e:
                st.error(f"Search Error: {e}")

# --- DIGITAL TIP JAR (THE LOG) ---
st.write("---")
st.subheader("📋 Session Request Log")

if st.session_state['nightly_requests']:
    req_df = pd.DataFrame(st.session_state['nightly_requests'])
    st.dataframe(req_df, use_container_width=True, hide_index=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Clear Log"):
            st.session_state['nightly_requests'] = []
            st.rerun()
    with col2:
        csv_log = req_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Nightly Request Report", data=csv_log, file_name="Nightly_Requests.csv", use_container_width=True)
else:
    st.caption("System ready. Waiting for the first request of the night.")
