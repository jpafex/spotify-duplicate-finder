import streamlit as st
import pandas as pd
import spotipy
import time
import re
import random
import requests
from datetime import datetime
from afexcloud.layout import bootstrap_page
from afexcloud.spotify_auth import get_auth_manager, get_valid_token_info

# 1. Page Config
st.set_page_config(page_title="Sidecar Scraper | AfexCloud", page_icon="🕵️", layout="wide")

# 2. Bootstrap Style & Security
auth_manager, token_info = bootstrap_page()

# 3. DNA Mapping Helpers (From your local script)
KEY_MAP = {
    0: "C", 1: "C#", 2: "D", 3: "D#", 4: "E", 5: "F",
    6: "F#", 7: "G", 8: "G#", 9: "A", 10: "A#", 11: "B"
}

# --- 4. THE HYBRID ENGINE ---
def get_track_dna(sp, track_ids):
    """Fetches DNA via API first (Fastest)"""
    try:
        # Spotify allows 100 tracks per request for audio features
        features = sp.audio_features(track_ids)
        return features
    except:
        return [None] * len(track_ids)

def fallback_web_scrape(name, artist):
    """Fallback Scraper if API fails (The 'Resilient Lark' logic)"""
    query = f"{name} {artist}".replace(" ", "+")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        # Targeting Tunebat via your team's successful search logic
        r = requests.get(f"https://tunebat.com/Search?q={query}", headers=headers, timeout=5)
        match = re.search(r'data-key="([^"]+)"', r.text)
        bpm_match = re.search(r'data-bpm="(\d+)"', r.text)
        return (match.group(1) if match else "N/A", bpm_match.group(1) if bpm_match else "N/A")
    except:
        return "N/A", "N/A"

# --- 5. TOOL INTERFACE ---
st.title("🕵️ Sidecar Scraper")
st.info("Paste a Playlist URL or ID below to fetch Key and BPM data using the High-Speed Hybrid Engine.")

# THE MISSING INPUT BOX
playlist_input = st.text_input("🔗 Spotify Playlist URL or ID:", placeholder="https://open.spotify.com/playlist/...")

if st.button("🚀 Run DNA Analysis"):
    if not playlist_input:
        st.warning("Please enter a playlist link first!")
    elif not token_info:
        st.error("Please connect Spotify in the sidebar first.")
    else:
        sp = spotipy.Spotify(auth_manager=auth_manager)
        
        # Extract ID
        p_id = playlist_input.split('/')[-1].split('?')[0] if '/' in playlist_input else playlist_input
        
        with st.spinner("Executing high-speed retrieval..."):
            try:
                # Get Playlist Tracks
                results = sp.playlist_tracks(p_id)
                tracks = results['items']
                
                dna_data = []
                # Process in batches of 50 for stability
                for i in range(0, len(tracks), 50):
                    batch = tracks[i:i+50]
                    t_ids = [t['track']['id'] for t in batch if t['track']]
                    
                    # Try API First (Your fast local logic)
                    features = get_track_dna(sp, t_ids)
                    
                    for idx, t in enumerate(batch):
                        track_obj = t['track']
                        f = features[idx]
                        
                        if f:
                            key_name = f"{KEY_MAP.get(f['key'], 'N/A')} {'Major' if f['mode'] == 1 else 'Minor'}"
                            bpm = round(f['tempo'])
                            source = "API (Fast)"
                        else:
                            # Trigger Web Scrape Fallback
                            key_name, bpm = fallback_web_scrape(track_obj['name'], track_obj['artists'][0]['name'])
                            source = "Web (Fallback)"
                            
                        dna_data.append({
                            "Name": track_obj['name'],
                            "Artist": track_obj['artists'][0]['name'],
                            "Key": key_name,
                            "BPM": bpm,
                            "Source": source,
                            "Spotify ID": track_obj['id']
                        })
                
                # Display Results in the "Table of Sorts"
                df = pd.DataFrame(dna_data)
                st.success(f"Analysis complete! Found {len(df)} tracks.")
                
                # The Lark's Interactive Table
                st.data_editor(
                    df,
                    hide_index=True,
                    use_container_width=True,
                    disabled=df.columns # Make it read-only but copy-paste friendly
                )
                
                # Download for logs
                safe_proj = st.session_state.get("global_proj", "Project").replace(" ", "_")
                st.download_button(
                    "📥 Download DNA Log (CSV)",
                    df.to_csv(index=False).encode('utf-8'),
                    f"{safe_proj}_DNA_Analysis.csv",
                    "text/csv"
                )
                
            except Exception as e:
                st.error(f"Analysis failed: {e}")
