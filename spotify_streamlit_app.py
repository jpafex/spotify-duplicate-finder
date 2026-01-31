import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import pandas as pd
from math import ceil
import io
import zipfile
import time
import re
import unicodedata
import requests
import random
from collections import defaultdict
from datetime import datetime

# Page config
st.set_page_config(page_title="AfexCloud Dashboard", page_icon="☁️", layout="wide")

# --- 1. GLOBAL STATE ---
if 'password_correct' not in st.session_state:
    st.session_state['password_correct'] = False
if 'global_proj' not in st.session_state:
    st.session_state['global_proj'] = ""

# --- 2. LOGIN GATE ---
def check_password():
    if st.session_state.get("password_correct"):
        return True
    st.title("🔐 AfexCloud Tool Login")
    with st.form("login_form"):
        u, p = st.text_input("Username"), st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if u == st.secrets["APP_USER"] and p == st.secrets["APP_PASS"]:
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("Invalid credentials.")
    return False

if check_password():
    # --- 3. AUTHENTICATION ---
    def get_auth_manager():
        scope = "playlist-modify-public playlist-modify-private playlist-read-private"
        return SpotifyOAuth(
            client_id=st.secrets["SPOTIFY_CLIENT_ID"],
            client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"],
            redirect_uri=st.secrets["SPOTIFY_REDIRECT_URI"],
            scope=scope, open_browser=False, cache_path=".cache-token"
        )

    auth_manager = get_auth_manager()
    token_info = auth_manager.validate_token(auth_manager.cache_handler.get_cached_token())

    # --- 4. ADVANCED HELPERS ---
    def clean_music_title(text):
        """Removes noise like 'Remastered', 'feat.', etc. to help scrapers"""
        text = re.sub(r'\(.*?\)|\[.*?\]', '', text) # Remove brackets
        text = re.sub(r'(?i)feat\.|featuring|remastered|radio edit|original mix|extended', '', text)
        return text.strip()

    def get_playlist_metadata(url_or_id):
        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=st.secrets["SPOTIFY_CLIENT_ID"], client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"]
        ))
        p_id = url_or_id.split('/')[-1].split('?')[0] if '/' in url_or_id else url_or_id
        try:
            meta = sp.playlist(p_id, fields="name")
            p_name, tracks, results = meta['name'], [], sp.playlist_tracks(p_id)
            pos = 1
            while results:
                for item in results['items']:
                    if item.get('track'):
                        t = item['track']
                        tracks.append({
                            'Original Pos': pos, 'Spotify - id': t.get('id'), 
                            'Name': t.get('name', 'Unknown'), 
                            'Artist': t['artists'][0]['name'] if t.get('artists') else 'Unknown',
                            'Album': t['album']['name'] if t.get('album') else 'Unknown'
                        })
                        pos += 1
                results = sp.next(results) if results['next'] else None
            return p_name, tracks
        except: return "Unknown", []

    # --- 5. THE RESILIENT SCRAPER ENGINE ---
    def hunt_dna_v3(name, artist):
        """Triple-source hunter with query sanitization"""
        clean_name = clean_music_title(name)
        query = f"{clean_name} {artist}".replace(" ", "+")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/'
        }
        
        # Source 1: Tunebat (Updated Pattern)
        try:
            r = requests.get(f"https://tunebat.com/Search?q={query}", headers=headers, timeout=10)
            # Find the first 'Info' link
            match = re.search(r'href="(/Info/[^"]+)"', r.text)
            if match:
                time.sleep(random.uniform(1.2, 2.5))
                r_info = requests.get(f"https://tunebat.com{match.group(1)}", headers=headers, timeout=10)
                # Flexible regex for data attributes or labels
                key = re.search(r'data-key="([^"]+)"', r_info.text) or re.search(r'>Key<.*?secondary-label">([^<]+)', r_info.text, re.S)
                bpm = re.search(r'data-bpm="(\d+)"', r_info.text) or re.search(r'>BPM<.*?secondary-label">([^<]+)', r_info.text, re.S)
                if key and bpm:
                    return key.group(1).strip(), bpm.group(1).strip(), "Tunebat"
        except: pass

        # Source 2: SongBPM.com
        try:
            r_sb = requests.get(f"https://songbpm.com/searches/{query}", headers=headers, timeout=10)
            bpm = re.search(r'class="bpm">(\d+)</span>', r_sb.text)
            key = re.search(r'class="key">([^<]+)</span>', r_sb.text)
            if bpm and key: return key.group(1).strip(), bpm.group(1).strip(), "SongBPM"
        except: pass

        return "Not Found", "Not Found", "None"

    # --- 6. SIDEBAR NAVIGATION ---
    with st.sidebar:
        st.title("☁️ AfexCloud")
        st.write("---")
        st.session_state['global_proj'] = st.text_input("📁 Global Project:", value=st.session_state['global_proj'])
        if st.button("🔄 Reset Project"):
            st.session_state['global_proj'] = ""; st.rerun()
        
        choice = st.radio("Select a Tool:", 
            ["🏠 Home", "🔍 Duplicate Finder", "📋 Song Lister", "📦 Batch Manager", "💿 Library Auditor", "📊 Collection Reviewer", "🗑️ Playlist Deleter", "🕵️ Sidecar Scraper"])
        
        st.write("---")
        if st.button("🚪 Log Out"):
            st.session_state["password_correct"] = False; st.rerun()

    safe_proj = re.sub(r'[^a-zA-Z0-9_]', '_', st.session_state['global_proj'])

    # --- 7. TOOLS ---
    if choice == "🕵️ Sidecar Scraper":
        st.title("🕵️ Sidecar Musical Scraper (v3.1)")
        st.info("No API Costs. Using the 'Resilient Lark' engine to hunt DNA on Tunebat & SongBPM.")
        inv_f = st.file_uploader("Upload Inventory CSV (from Song Lister)", type="csv")
        
        if inv_f:
            df_inv = pd.read_csv(inv_f)
            if st.button("🚀 Start Multi-Source Scrape"):
                results, prog = [], st.progress(0)
                status_text = st.empty()
                
                for i, row in df_inv.iterrows():
                    status_text.write(f"Scraping ({i+1}/{len(df_inv)}): **{row['Name']}**")
                    k, b, src = hunt_dna_v3(row['Name'], row['Artist'])
                    
                    # Add Manual Link if not found
                    manual_link = ""
                    if k == "Not Found":
                        q_manual = f"{row['Name']} {row['Artist']}".replace(" ", "+")
                        manual_link = f"https://tunebat.com/Search?q={q_manual}"
                    
                    results.append({'Key': k, 'BPM': b, 'Source': src, 'Manual Link': manual_link})
                    prog.progress((i + 1) / len(df_inv))
                    time.sleep(random.uniform(1.0, 2.0))
                
                df_final = pd.concat([df_inv, pd.DataFrame(results)], axis=1)
                st.success("DNA Hunt Complete!")
                st.dataframe(df_final, use_container_width=True, hide_index=True)
                st.download_button("📥 Download Master DJ Log", df_final.to_csv(index=False).encode('utf-8'), f"{safe_proj}_Master_DJ_Log.csv", "text/csv")

    # (Previous tools like Song Lister, Batch Manager, etc. are included in the full logic)
    elif choice == "📋 Song Lister":
        st.title(f"📋 Song Lister: {st.session_state['global_proj']}")
        url = st.text_input("Enter Playlist URL/ID:")
        if st.button("Generate Inventory"):
            p_name, tracks = get_playlist_metadata(url)
            if tracks:
                df = pd.DataFrame(tracks)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.download_button("📥 Download Inventory", df.to_csv(index=False).encode('utf-8'), f"{safe_proj}_inventory.csv", "text/csv")

    # (Other tool logic blocks for Duplicate Finder, Batch Manager, Auditor, Reviewer, Deleter)

# --- FINAL FOOTER ---
st.write("---")
cur_p = st.session_state.get('global_proj', 'Default')
st.caption(f"AfexCloud v3.0.1 | Project: {cur_p if cur_p else 'Default'} | Multi-Source Scraper Active")

