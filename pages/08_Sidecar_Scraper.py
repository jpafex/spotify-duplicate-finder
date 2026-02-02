import streamlit as st
import pandas as pd
import requests
import base64
import time
from afexcloud.layout import bootstrap_page

# 1. Page Config
st.set_page_config(page_title="Sidecar Scraper | AfexCloud", page_icon="🕵️", layout="wide")

# 2. Bootstrap Style
bootstrap_page()

# 3. Isolated Token Engine (Directly from your working local script)
def get_isolated_token():
    client_id = st.secrets["SPOTIFY_CLIENT_ID"]
    client_secret = st.secrets["SPOTIFY_CLIENT_SECRET"]
    url = "https://accounts.spotify.com/api/token"
    auth_str = f"{client_id}:{client_secret}"
    auth_b64 = base64.b64encode(auth_str.encode()).decode()
    
    # MIMICRY HEADERS: Making the cloud look like a local machine
    headers = {
        'Authorization': f'Basic {auth_b64}',
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) GitBash/2.43.0'
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
st.title("🕵️ Sidecar Scraper (v3.7)")
st.info("Git-Bash Mimicry Active: Attempting to bypass Cloud restrictions using localized headers.")

playlist_input = st.text_input("🔗 Spotify Playlist URL or ID:", placeholder="Paste link here...")

if st.button("🚀 Mirror Bash Analysis"):
    if not playlist_input:
        st.warning("Please enter a playlist link.")
    else:
        with st.spinner("Executing Git-Bash mimicry engine..."):
            token = get_isolated_token()
            
            # HEADERS: Added User-Agent to every request
            headers = {
                'Authorization': f'Bearer {token}',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            }
            
            p_id = playlist_input.split('/')[-1].split('?')[0] if '/' in playlist_input else playlist_input
            
            try:
                # 1. Fetch Tracks (Market-Locked for US stability)
                all_items = []
                url = f"https://api.spotify.com/v1/playlists/{p_id}/tracks?limit=100&market=US"
                while url:
                    res = requests.get(url, headers=headers).json()
                    all_items.extend(res.get('items', []))
                    url = res.get('next')

                if not all_items:
                    st.error("Empty response. Check your Spotify Secrets.")
                else:
                    dna_results = []
                    # 2. Slow-Burn Batching (Groups of 20)
                    for i in range(0, len(all_items), 20):
                        batch = all_items[i:i+20]
                        valid_tracks = [t['track'] for t in batch if t.get('track') and t['track'].get('id')]
                        ids = [track['id'] for track in valid_tracks]

                        if not ids: continue

                        # 3. Request Audio Features
                        feat_url = f"https://api.spotify.com/v1/audio-features?ids={','.join(ids)}"
                        feat_res = requests.get(feat_url, headers=headers).json()
                        features_list = feat_res.get('audio_features', [])

                        # 4. Bulletproof Mapping
                        feat_map = {f['id']: f for f in features_list if f is not None}
                        
                        for track in valid_tracks:
                            f = feat_map.get(track['id'])
                            key_text, bpm = "N/A", 0
                            
                            if f:
                                k_name = KEY_MAP.get(f['key'], 'N/A')
                                mode = "Major" if f['mode'] == 1 else "Minor"
                                key_text = f"{k_name} {mode}"
                                bpm = round(f['tempo'])
                            
                            dna_results.append({
                                "Name": track['name'],
                                "Artist": track['artists'][0]['name'],
                                "Key": key_text,
                                "BPM": bpm,
                                "Spotify URI": f"spotify:track:{track['id']}"
                            })

                    df = pd.DataFrame(dna_results)
                    st.success(f"Mimicry Complete! {len(df)} tracks analyzed.")
                    st.data_editor(df, hide_index=True, use_container_width=True)
                    
                    st.download_button(
                        "📥 Download Master DJ Log",
                        df.to_csv(index=False).encode('utf-8'),
                        "DNA_Log.csv", "text/csv"
                    )
            except Exception as e:
                st.error(f"Environmental Block Detected: {e}")
