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

# --- 1. GLOBAL STATE INITIALIZATION ---
if 'password_correct' not in st.session_state:
    st.session_state['password_correct'] = False
if 'global_proj' not in st.session_state:
    st.session_state['global_proj'] = ""

# --- 2. SECURE LOGIN GATE ---
def check_password():
    if st.session_state.get("password_correct"):
        return True
    
    st.title("🔐 AfexCloud Tool Login")
    with st.form("login_form"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if u == st.secrets["APP_USER"] and p == st.secrets["APP_PASS"]:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Invalid credentials.")
    return False

if check_password():
    
    # --- 3. AUTHENTICATION ENGINES ---
    def get_auth_manager():
        scope = "playlist-modify-public playlist-modify-private playlist-read-private"
        return SpotifyOAuth(
            client_id=st.secrets["SPOTIFY_CLIENT_ID"],
            client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"],
            redirect_uri=st.secrets["SPOTIFY_REDIRECT_URI"],
            scope=scope,
            open_browser=False,
            cache_path=".cache-token"
        )

    auth_manager = get_auth_manager()
    token_info = auth_manager.validate_token(auth_manager.cache_handler.get_cached_token())

    if "code" in st.query_params and not token_info:
        try:
            auth_manager.get_access_token(st.query_params.get("code"), as_dict=False)
            st.query_params.clear()
        except: pass

    # --- 4. ADVANCED HELPERS ---
    def advanced_normalize(text):
        if not isinstance(text, str): text = str(text)
        try: text = text.encode('cp1252').decode('utf-8')
        except: pass
        text = unicodedata.normalize('NFKD', text)
        text = "".join([c for c in text if not unicodedata.combining(c)])
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s]', '', text)
        return re.sub(r'\s+', ' ', text).strip()

    def get_playlist_metadata(url_or_id):
        sp_read = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=st.secrets["SPOTIFY_CLIENT_ID"], client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"]
        ))
        p_id = url_or_id.split('/')[-1].split('?')[0] if '/' in url_or_id else url_or_id
        try:
            meta = sp_read.playlist(p_id, fields="name")
            p_name = meta['name']
            tracks = []
            results = sp_read.playlist_tracks(p_id)
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
                results = sp_read.next(results) if results['next'] else None
            return p_name, tracks
        except: return "Unknown", []

    # --- 5. THE TRIPLE-SOURCE SCRAPER ENGINE ---
    def hunt_dna(name, artist):
        query = f"{name} {artist}".replace(" ", "+")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        
        # Source 1: Tunebat Deep Hunt
        try:
            r = requests.get(f"https://tunebat.com/Search?q={query}", headers=headers, timeout=8)
            match = re.search(r'href="(/Info/[^"]+)"', r.text)
            if match:
                time.sleep(random.uniform(0.5, 1.2))
                r_info = requests.get(f"https://tunebat.com{match.group(1)}", headers=headers, timeout=8)
                key = re.search(r'>Key<.*?secondary-label">([^<]+)', r_info.text, re.S)
                bpm = re.search(r'>BPM<.*?secondary-label">([^<]+)', r_info.text, re.S)
                if key and bpm: return key.group(1).strip(), bpm.group(1).strip(), "Tunebat"
        except: pass

        # Source 2: GetSongBPM Fallback
        try:
            r_gsb = requests.get(f"https://getsongbpm.com/search?q={query}", headers=headers, timeout=8)
            key = re.search(r'data-key="([^"]+)"', r_gsb.text)
            bpm = re.search(r'data-bpm="(\d+)"', r_gsb.text)
            if key and bpm: return key.group(1).strip(), bpm.group(1).strip(), "GetSongBPM"
        except: pass

        return "Not Found", "Not Found", "None"

    # --- 6. SIDEBAR NAVIGATION ---
    with st.sidebar:
        st.title("☁️ AfexCloud")
        st.write("---")
        st.session_state['global_proj'] = st.text_input("📁 Global Project:", value=st.session_state['global_proj'])
        if st.button("🔄 Reset Project"):
            st.session_state['global_proj'] = ""; st.rerun()
        st.write("---")
        if token_info: st.success("🟢 Spotify: Connected")
        else: st.error("🔴 Spotify: Not Connected"); st.markdown(f"[Connect Spotify]({auth_manager.get_authorize_url()})")

        choice = st.radio("Select a Tool:", 
            ["🏠 Home", "🔍 Duplicate Finder", "📋 Song Lister", "📦 Batch Manager", "💿 Library Auditor", "📊 Collection Reviewer", "🗑️ Playlist Deleter", "🕵️ Sidecar Scraper"])
        
        st.write("---")
        if st.button("🚪 Log Out"):
            st.session_state["password_correct"] = False; st.rerun()

    safe_proj = re.sub(r'[^a-zA-Z0-9_]', '_', st.session_state['global_proj'])

    # --- 7. TOOLS ---
    
    if choice == "🏠 Home":
        st.title("🚀 AfexCloud Dashboard")
        st.info(f"Active Project: **{st.session_state['global_proj'] if st.session_state['global_proj'] else 'None Set'}**")

    elif choice == "🔍 Duplicate Finder":
        st.title(f"🔍 Duplicate Finder: {st.session_state['global_proj']}")
        url = st.text_input("Enter Playlist URL/ID:")
        if st.button("Scan"):
            p_name, tracks = get_playlist_metadata(url)
            if tracks:
                by_id = defaultdict(list)
                for t in tracks: by_id[t['Spotify - id']].append(t)
                dupes = [i for g in by_id.values() if len(g) > 1 for i in g]
                if dupes:
                    st.warning(f"Found {len(dupes)} duplicates.")
                    df_dupes = pd.DataFrame(dupes)
                    st.dataframe(df_dupes, use_container_width=True, hide_index=True)
                    st.download_button("📥 Download Dupes", df_dupes.to_csv(index=False).encode('utf-8'), f"{safe_proj}_dupes.csv", "text/csv")
                else: st.success("No duplicates found!")

    elif choice == "📋 Song Lister":
        st.title(f"📋 Song Lister: {st.session_state['global_proj']}")
        url = st.text_input("Enter Playlist URL/ID:")
        if st.button("Generate Inventory"):
            p_name, tracks = get_playlist_metadata(url)
            if tracks:
                df = pd.DataFrame(tracks)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.download_button("📥 Download Inventory", df.to_csv(index=False).encode('utf-8'), f"{safe_proj}_inventory.csv", "text/csv")

    elif choice == "📦 Batch Manager":
        st.title(f"📦 Batch Manager: {st.session_state['global_proj']}")
        tab1, tab2 = st.tabs(["Step 1: Create Batches", "Step 2: Upload"])
        with tab1:
            url = st.text_input("Source Playlist URL/ID:")
            if st.button("Generate Batches"):
                p_name, all_tracks = get_playlist_metadata(url)
                if all_tracks:
                    num_batches = ceil(len(all_tracks) / 25)
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w") as zf:
                        for i in range(num_batches):
                            batch = all_tracks[i*25 : (i+1)*25]
                            df_batch = pd.DataFrame(batch)[['Original Pos', 'Name', 'Artist', 'Album', 'Spotify - id']]
                            lbl = f"{batch[0]['Original Pos']}_to_{batch[-1]['Original Pos']}"
                            zf.writestr(f"{safe_proj}_Batch_{i+1}_{lbl}.csv", df_batch.to_csv(index=False).encode('utf-8'))
                    st.download_button("📦 DOWNLOAD ZIP", zip_buffer.getvalue(), f"{safe_proj}_Batches.zip", "application/zip")
        with tab2:
            if not token_info: st.warning("Connect Spotify first.")
            else:
                files = st.file_uploader("Upload Batch CSVs", accept_multiple_files=True, type="csv")
                if st.button("🚀 Create Spotify Playlists"):
                    sp_write = spotipy.Spotify(auth_manager=auth_manager)
                    for f in files:
                        df = pd.read_csv(f)
                        p = sp_write.user_playlist_create(user=sp_write.current_user()['id'], name=f"{st.session_state['global_proj']}: {f.name}", public=False)
                        sp_write.playlist_add_items(p['id'], [f"spotify:track:{tid}" for tid in df['Spotify - id'].tolist()])
                    st.balloons()

    elif choice == "💿 Library Auditor":
        st.title(f"💿 Library Auditor: {st.session_state['global_proj']}")
        c1, c2 = st.columns(2)
        with c1: inv_f = st.file_uploader("Spotify Inventory", type="csv")
        with c2: loc_f = st.file_uploader("Local Songs", type="csv")
        if inv_f and loc_f:
            if st.button("🔍 Run Audit"):
                df_inv, df_loc = pd.read_csv(inv_f), pd.read_csv(loc_f)
                df_inv['compare_key'] = df_inv.apply(lambda r: f"{advanced_normalize(r['Name'])}__{advanced_normalize(r['Artist'])}", axis=1)
                loc_keys = {f"{advanced_normalize(str(e).split(',')[0])}__{advanced_normalize(str(e).split(',')[1])}" for e in df_loc.iloc[:, 0] if len(str(e).split(',')) >= 2}
                missing_df = df_inv[~df_inv['compare_key'].isin(loc_keys)].copy()
                st.metric("Missing Tracks", len(missing_df))
                st.dataframe(missing_df[['Original Pos', 'Name', 'Artist', 'Album']], use_container_width=True, hide_index=True)
                st.download_button("📥 Download Missing", missing_df.to_csv(index=False).encode('utf-8'), f"{safe_proj}_Missing.csv", "text/csv")

    elif choice == "📊 Collection Reviewer":
        st.title(f"📊 Collection Reviewer: {st.session_state['global_proj']}")
        c1, c2 = st.columns(2)
        with c1: inv_f = st.file_uploader("Inventory", type="csv")
        with c2: loc_f = st.file_uploader("Local Library", type="csv")
        if inv_f and loc_f:
            if st.button("📊 Generate Smart Review"):
                df_inv, df_loc = pd.read_csv(inv_f), pd.read_csv(loc_f)
                inv_rows = [{'Source': 'Spotify', 'Key': f"{advanced_normalize(r['Name'])}__{advanced_normalize(r['Artist'])}", 'Name': r['Name'], 'Artist': r['Artist']} for _, r in df_inv.iterrows()]
                loc_rows = []
                for e in df_loc.iloc[:, 0]:
                    p = str(e).split(',')
                    if len(p) >= 2: loc_rows.append({'Source': 'Local', 'Key': f"{advanced_normalize(p[0])}__{advanced_normalize(p[1])}", 'Name': p[0], 'Artist': p[1]})
                master_df = pd.concat([pd.DataFrame(inv_rows), pd.DataFrame(loc_rows)]).sort_values(by=['Key', 'Source']).reset_index(drop=True)
                counts = master_df['Key'].value_counts()
                lone_wolf_keys = counts[counts == 1].index.tolist()
                st.metric("Mismatches", len(lone_wolf_keys), delta_color="inverse")
                st.dataframe(master_df.style.apply(lambda d: pd.DataFrame('background-color: #ffcccc' if d.name in lone_wolf_keys else '', index=d.index, columns=d.columns), axis=None), use_container_width=True, hide_index=True)
                st.download_button("📥 Download Report", master_df.to_csv(index=False).encode('utf-8'), f"{safe_proj}_Health.csv", "text/csv")

    elif choice == "🗑️ Playlist Deleter":
        st.title("🗑️ Playlist Deleter")
        if not token_info: st.warning("Connect Spotify first.")
        else:
            sp = spotipy.Spotify(auth_manager=auth_manager)
            if st.button("🔍 Load My Playlists"):
                st.session_state['my_playlists'] = sp.current_user_playlists(limit=50)['items']
            if 'my_playlists' in st.session_state:
                with st.form("del_form"):
                    to_del = []
                    for p in st.session_state['my_playlists']:
                        if st.checkbox(f"{p['name']} (ID: {p['id']})"): to_del.append({'id': p['id'], 'name': p['name']})
                    if st.form_submit_button("🔥 DELETE SELECTED"):
                        for item in to_del: sp.current_user_unfollow_playlist(item['id'])
                        st.success(f"Deleted {len(to_del)} playlists.")
                        log = pd.DataFrame(to_del)
                        st.download_button("📥 Download Deletion Proof", log.to_csv(index=False).encode('utf-8'), f"Deletion_Proof_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
                        del st.session_state['my_playlists']; st.rerun()

    elif choice == "🕵️ Sidecar Scraper":
        st.title("🕵️ Sidecar Musical Scraper (v3.0.1)")
        st.info("No API Costs. Using public music databases to build your DNA logs.")
        inv_f = st.file_uploader("Upload Inventory CSV", type="csv")
        
        if inv_f:
            df_inv = pd.read_csv(inv_f)
            if st.button("🚀 Start Multi-Source Scrape"):
                results, prog = [], st.progress(0)
                status_text = st.empty()
                for i, row in df_inv.iterrows():
                    status_text.write(f"Scraping ({i+1}/{len(df_inv)}): **{row['Name']}**")
                    k, b, src = hunt_dna(row['Name'], row['Artist'])
                    results.append({'Key': k, 'BPM': b, 'Source': src})
                    prog.progress((i + 1) / len(df_inv))
                    time.sleep(random.uniform(0.8, 1.5))
                
                df_final = pd.concat([df_inv, pd.DataFrame(results)], axis=1)
                st.success("DNA Hunt Complete!")
                st.dataframe(df_final, use_container_width=True, hide_index=True)
                st.download_button("📥 Download Master DJ Log", df_final.to_csv(index=False).encode('utf-8'), f"{safe_proj}_Master_DJ_Log.csv", "text/csv")

# --- FINAL FOOTER ---
st.write("---")
cur_p = st.session_state.get('global_proj', 'Default')
st.caption(f"AfexCloud v3.0.1 | Project: {cur_p if cur_p else 'Default'} | Multi-Source Scraper Active")
