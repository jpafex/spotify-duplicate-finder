import streamlit as st
import pandas as pd
import requests
import base64
import re
from datetime import datetime
from afexcloud.layout import bootstrap_page

# 1. Page Config
st.set_page_config(page_title="Sidecar Scraper | AfexCloud", page_icon="🕵️", layout="wide")

# 2. Bootstrap Style
bootstrap_page()

# 3. Isolated Token Engine (Client Credentials Flow)
def get_isolated_token():
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
st.title("🕵️ Sidecar Scraper (Robust Engine)")
st.info("Bypassing 403 errors with isolated token and safe ID mapping.")

playlist_input = st.text_input("🔗 Spotify Playlist URL or ID:", placeholder="Paste here...")

if st.button("🚀 Run DNA Analysis"):
    if not playlist_input:
        st.warning("Please enter a playlist link.")
    else:
        with st.spinner("Analyzing tracks..."):
            token = get_isolated_token()
            headers = {'Authorization': f'Bearer {token}'}
            
            p_id = playlist_input.split('/')[-1].split('?')[0] if '/' in playlist_input else playlist_input
            
            try:
                # 1. Paginated Track Retrieval (Gets all songs, not just first 100)
                all_items = []
                url = f"https://api.spotify.com/v1/playlists/{p_id}/tracks"
                while url:
                    res = requests.get(url, headers=headers)
                    data = res.json()
                    all_items.extend(data.get('items', []))
                    url = data.get('next')

                if not all_items:
                    st.error("No tracks found.")
                else:
                    dna_data = []
                    # 2. Batch DNA Fetching (100 at a time)
                    for i in range(0, len(all_items), 100):
                        batch = all_items[i:i+100]
                        # Filter for valid tracks with IDs
                        valid_tracks = [t['track'] for t in batch if t.get('track') and t['track'].get('id')]
                        ids = [t['id'] for t in valid_tracks]
                        
                        if not ids: continue

                        # 3. Get Audio Features
                        feat_res = requests.get(f"https://api.spotify.com/v1/audio-features?ids={','.join(ids)}", headers=headers)
                        features_list = feat_res.json().get('audio_features', [])
                        
                        # Create a lookup map to avoid "Index Out of Range" errors
                        feat_map = {f['id']: f for f in features_list if f}
                        
                        for track in valid_tracks:
                            f = feat_map.get(track['id'])
                            key_text, bpm = "N/A", 0
                            
                            if f:
                                mode = "Major" if f['mode'] == 1 else "Minor"
                                key_text = f"{KEY_MAP.get(f['key'], 'N/A')} {mode}"
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
                    
                    # Interactive Table for copying and link checking
                    st.data_editor(
                        df,
                        hide_index=True,
                        use_container_width=True,
                        column_config={"Web Link": st.column_config.LinkColumn()},
                        disabled=df.columns
                    )
                    
                    # Log Download
                    safe_proj = st.session_state.get("global_proj", "Project").replace(" ", "_")
                    st.download_button(
                        "📥 Download Master DNA Log",
                        df.to_csv(index=False).encode('utf-8'),
                        f"{safe_proj}_DNA_Log.csv",
                        "text/csv"
                    )
            except Exception as e:
                st.error(f"Analysis failed: {e}")
