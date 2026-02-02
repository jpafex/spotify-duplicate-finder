import streamlit as st
import pandas as pd
import requests
import base64
import re
from datetime import datetime
from afexcloud.layout import bootstrap_page

# 1. Page Config
st.set_page_config(page_title="Sidecar Scraper | AfexCloud", page_icon="🕵️", layout="wide")

# 2. Bootstrap Style (We still want the branding/sidebar)
bootstrap_page()

# 3. Isolated Token Engine (Directly from your local logic)
def get_isolated_token():
    """Bypasses user login to get a high-speed app token."""
    client_id = st.secrets["SPOTIFY_CLIENT_ID"]
    client_secret = st.secrets["SPOTIFY_CLIENT_SECRET"]
    
    url = "https://accounts.spotify.com/api/token"
    auth_str = f"{client_id}:{client_secret}"
    auth_b64 = base64.b64encode(auth_str.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_b64}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {'grant_type': 'client_credentials'}
    
    response = requests.post(url, headers=headers, data=data)
    return response.json().get('access_token')

# 4. DNA Mapping
KEY_MAP = {
    0: "C", 1: "C#", 2: "D", 3: "D#", 4: "E", 5: "F",
    6: "F#", 7: "G", 8: "G#", 9: "A", 10: "A#", 11: "B"
}

# --- TOOL INTERFACE ---
st.title("🕵️ Sidecar Scraper (Isolated Engine)")
st.info("This tool uses an independent high-speed token to bypass 403 errors.")

playlist_input = st.text_input("🔗 Spotify Playlist URL or ID:", placeholder="Paste here...")

if st.button("🚀 Run DNA Analysis"):
    if not playlist_input:
        st.warning("Please enter a playlist link.")
    else:
        with st.spinner("Fetching isolated token and analyzing tracks..."):
            token = get_isolated_token()
            headers = {'Authorization': f'Bearer {token}'}
            
            # Extract ID
            p_id = playlist_input.split('/')[-1].split('?')[0] if '/' in playlist_input else playlist_input
            
            try:
                # 1. Get Tracks
                res = requests.get(f"https://api.spotify.com/v1/playlists/{p_id}/tracks", headers=headers)
                items = res.json().get('items', [])
                
                if not items:
                    st.error("No tracks found. Check if the playlist ID is correct.")
                else:
                    dna_data = []
                    # Process in batches of 100 for DNA
                    for i in range(0, len(items), 100):
                        batch = items[i:i+100]
                        ids = [t['track']['id'] for t in batch if t['track'] and t['track']['id']]
                        
                        # 2. Get Audio Features
                        feat_res = requests.get(f"https://api.spotify.com/v1/audio-features?ids={','.join(ids)}", headers=headers)
                        features = feat_res.json().get('audio_features', [])
                        
                        for idx, t in enumerate(batch):
                            track = t['track']
                            f = features[idx]
                            
                            key_text = "N/A"
                            bpm = 0
                            if f:
                                key_name = KEY_MAP.get(f['key'], 'N/A')
                                mode = "Major" if f['mode'] == 1 else "Minor"
                                key_text = f"{key_name} {mode}"
                                bpm = round(f['tempo'])
                            
                            dna_data.append({
                                "Name": track['name'],
                                "Artist": track['artists'][0]['name'],
                                "Key": key_text,
                                "BPM": bpm,
                                "Web Link": f"https://open.spotify.com/track/{track['id']}",
                                "Spotify URI": f"spotify:track:{track['id']}"
                            })

                    df = pd.DataFrame(dna_data)
                    st.success(f"Analysis complete! {len(df)} tracks found.")
                    
                    # The "Table of Sorts" for the Larks
                    st.data_editor(
                        df,
                        hide_index=True,
                        use_container_width=True,
                        column_config={
                            "Web Link": st.column_config.LinkColumn(),
                        }
                    )
                    
                    # Download CSV
                    safe_proj = st.session_state.get("global_proj", "Project").replace(" ", "_")
                    st.download_button(
                        "📥 Download DNA Log",
                        df.to_csv(index=False).encode('utf-8'),
                        f"{safe_proj}_DNA_Log.csv",
                        "text/csv"
                    )
            except Exception as e:
                st.error(f"Analysis failed: {e}")
