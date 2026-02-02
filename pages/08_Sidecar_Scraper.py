import streamlit as st
import pandas as pd
import spotipy
import time
import re
from datetime import datetime
from afexcloud.layout import bootstrap_page
from afexcloud.spotify_auth import get_auth_manager, get_valid_token_info

# 1. Page Config
st.set_page_config(page_title="Sidecar Scraper | AfexCloud", page_icon="🕵️", layout="wide")

# 2. Bootstrap Style & Security
auth_manager, token_info = bootstrap_page()

# 3. DNA Mapping (Matches your local working script)
KEY_MAP = {
    0: "C", 1: "C#", 2: "D", 3: "D#", 4: "E", 5: "F",
    6: "F#", 7: "G", 8: "G#", 9: "A", 10: "A#", 11: "B"
}

# 4. Tool Logic
st.title("🕵️ Sidecar Scraper")
st.info("High-speed DNA retrieval. Paste your playlist link below to fetch Key and BPM.")

# THE INPUT BOX: This is where you paste the Playlist ID/URL
playlist_input = st.text_input("🔗 Spotify Playlist URL or ID:", placeholder="https://open.spotify.com/playlist/...")

if st.button("🚀 Run Analysis"):
    if not playlist_input:
        st.warning("Please enter a playlist URL or ID first.")
    elif not token_info:
        st.error("Spotify is not connected. Please connect in the sidebar.")
    else:
        # We use the token from the Lark's login
        sp = spotipy.Spotify(auth=token_info['access_token'])
        
        # Extract ID from URL
        p_id = playlist_input.split('/')[-1].split('?')[0] if '/' in playlist_input else playlist_input
        
        try:
            with st.spinner("Analyzing tracks..."):
                # Fetch playlist tracks
                results = sp.playlist_tracks(p_id)
                tracks = results['items']
                
                if not tracks:
                    st.error("No tracks found. Is this playlist private or empty?")
                    st.stop()

                dna_results = []
                # Process in batches of 50 for maximum speed
                for i in range(0, len(tracks), 50):
                    batch = tracks[i:i+50]
                    t_ids = [t['track']['id'] for t in batch if t['track'] and t['track']['id']]
                    
                    # Fetch Audio Features (Key/BPM)
                    features = sp.audio_features(t_ids)
                    
                    for idx, t in enumerate(batch):
                        track_info = t['track']
                        feat = features[idx]
                        
                        if feat:
                            key_name = f"{KEY_MAP.get(feat['key'], 'N/A')} {'Major' if feat['mode'] == 1 else 'Minor'}"
                            bpm = round(feat['tempo'])
                        else:
                            key_name, bpm = "Not Found", "Not Found"
                            
                        dna_results.append({
                            "Name": track_info['name'],
                            "Artist": track_info['artists'][0]['name'],
                            "Key": key_name,
                            "BPM": bpm,
                            "Spotify ID": track_info['id']
                        })

                # Display the "Table of Sorts"
                df = pd.DataFrame(dna_results)
                st.success(f"Analysis complete! Found {len(df)} tracks.")
                
                # Interactive Table: Highlight and copy (Ctrl+C) any line!
                st.data_editor(
                    df,
                    hide_index=True,
                    use_container_width=True,
                    disabled=df.columns # Read-only but copy-paste friendly
                )
                
                # Project-based download
                safe_proj = st.session_state.get("global_proj", "Project").replace(" ", "_")
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Download Master DJ Log (CSV)",
                    csv_data,
                    f"{safe_proj}_DNA_Log.csv",
                    "text/csv"
                )
                
        except Exception as e:
            st.error(f"Analysis bombed! Error: {e}")
            st.write("Tip: If you see a 403 error, the playlist might be private.")
