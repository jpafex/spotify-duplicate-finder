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
from collections import defaultdict
from datetime import datetime, timedelta

# Page config
st.set_page_config(page_title="AfexCloud Dashboard", page_icon="☁️", layout="wide")

# --- 1. GLOBAL STATE & AUTH FIX ---
# We initialize state at the very top to ensure it survives the rerun
if 'password_correct' not in st.session_state:
    st.session_state['password_correct'] = False
if 'global_proj' not in st.session_state:
    st.session_state['global_proj'] = ""

# --- 2. SECURE LOGIN GATE (Logic Re-organized) ---
def check_password():
    """Returns True if the user had the correct password."""
    def password_entered():
        if st.session_state["username"] == st.secrets["APP_USER"] and \
           st.session_state["password"] == st.secrets["APP_PASS"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.title("🔐 AfexCloud Tool Login")
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password")
        st.button("Login", on_click=password_entered)
        return False
    return True

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

    # --- THE "DOUBLE LOGIN" FIX ---
    # We handle the 'code' parameter silently without forced reruns that break the session
    if "code" in st.query_params and not token_info:
        try:
            auth_manager.get_access_token(st.query_params.get("code"), as_dict=False)
            st.query_params.clear() # Clear the code from URL
        except:
            pass

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
            client_id=st.secrets["SPOTIFY_CLIENT_ID"],
            client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"]
        ))
        p_id = url_or_id.split('/')[-1].split('?')[0] if '/' in url_or_id else url_or_id
        try:
            meta = sp_read.playlist(p_id, fields="name")
            p_name = meta['name']
            tracks = []
            results = sp_read.playlist_tracks(p_id)
            current_pos = 1
            while results:
                for item in results['items']:
                    if item.get('track'):
                        t = item['track']
                        tracks.append({
                            'Original Pos': current_pos, 
                            'Spotify - id': t.get('id'), 
                            'Name': t.get('name', 'Unknown'), 
                            'Artist': t['artists'][0]['name'] if t.get('artists') else 'Unknown', 
                            'Album': t['album']['name'] if t.get('album') else 'Unknown'
                        })
                        current_pos += 1
                results = sp_read.next(results) if results['next'] else None
            return p_name, tracks
        except Exception as e:
            st.error(f"Spotify API Error: {e}")
            return "Unknown", []

    # --- NEW: SIDECAR SCRAPER LOGIC ---
    def scrape_key_bpm(track_name, artist_name):
        """Scrapes Tunebat for Key and BPM data without API"""
        query = f"{track_name} {artist_name}".replace(" ", "%20")
        url = f"https://tunebat.com/Search?q={query}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            # Simple regex search based on your team's provided scraper
            key_search = re.search(r'data-key="([^"]+)"', resp.text)
            bpm_search = re.search(r'data-bpm="([^"]+)"', resp.text)
            return (key_search.group(1) if key_search else "Not Found", 
                    bpm_search.group(1) if bpm_search else "Not Found")
        except:
            return "Error", "Error"

    # --- 5. SIDEBAR NAVIGATION ---
    with st.sidebar:
        st.title("☁️ AfexCloud")
        st.write("---")
        st.session_state['global_proj'] = st.text_input("📁 Global Project Name:", value=st.session_state['global_proj'])
        if st.button("🔄 Start New Project (Reset)"):
            st.session_state['global_proj'] = ""
            st.rerun()
        st.write("---")
        if token_info: st.success("🟢 Spotify: Connected")
        else: st.error("🔴 Spotify: Not Connected"); st.markdown(f"[Connect Spotify]({auth_manager.get_authorize_url()})")

        choice = st.radio("Select a Tool:", 
            ["🏠 Home", "🔍 Duplicate Finder", "📋 Song Lister", "📦 Batch Manager", "💿 Library Auditor", "📊 Collection Reviewer", "🗑️ Playlist Deleter", "🕵️ Sidecar Scraper"])
        
        st.write("---")
        if st.button("🚪 Log Out"):
            st.session_state["password_correct"] = False
            st.rerun()

    safe_proj = re.sub(r'[^a-zA-Z0-9_]', '_', st.session_state['global_proj'])

    # --- 6. TOOLS ---
    
    if choice == "🏠 Home":
        st.title("🚀 AfexCloud Marketing Dashboard")
        st.info(f"Active Project: **{st.session_state['global_proj'] if st.session_state['global_proj'] else 'None Set'}**")

    elif choice == "🔍 Duplicate Finder":
        st.title(f"🔍 Duplicate Finder: {st.session_state['global_proj']}")
        url = st.text_input("Enter Playlist URL/ID:")
        if st.button("Run Scan"):
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
                    clean_p_name = re.sub(r'[^a-zA-Z0-9_]', '_', p_name)
                    with zipfile.ZipFile(zip_buffer, "w") as zf:
                        for i in range(num_batches):
                            batch = all_tracks[i*25 : (i+1)*25]
                            df_batch = pd.DataFrame(batch)[['Original Pos', 'Name', 'Artist', 'Album', 'Spotify - id']]
                            range_lbl = f"{batch[0]['Original Pos']}_to_{batch[-1]['Original Pos']}"
                            c_name = f"{safe_proj + '_' if safe_proj else ''}{clean_p_name}_Batch_{i+1}_{range_lbl}.csv"
                            zf.writestr(c_name, df_batch.to_csv(index=False).encode('utf-8'))
                    st.download_button(f"📦 DOWNLOAD ZIP", zip_buffer.getvalue(), f"{safe_proj}_Batches.zip", "application/zip")
        with tab2:
            if not token_info: st.warning("Connect Spotify first.")
            else:
                files = st.file_uploader("Upload Batch CSVs", accept_multiple_files=True, type="csv")
                if st.button("🚀 Create Spotify Playlists"):
                    sp_write = spotipy.Spotify(auth_manager=auth_manager)
                    for f in files:
                        df = pd.read_csv(f)
                        p = sp_write.user_playlist_create(user=sp_write.current_user()['id'], name=f"{st.session_state['global_proj'] if st.session_state['global_proj'] else 'Batch'}: {f.name}", public=False)
                        sp_write.playlist_add_items(p['id'], [f"spotify:track:{tid}" for tid in df['Spotify - id'].tolist()])
                    st.balloons()

    elif choice == "💿 Library Auditor":
        st.title(f"💿 Library Auditor: {st.session_state['global_proj']}")
        c1, c2 = st.columns(2)
        with c1: inv_f = st.file_uploader("Spotify Inventory", type=["csv", "xlsx"], key="aud_inv")
        with c2: loc_f = st.file_uploader("Local Songs", type=["csv", "xlsx"], key="aud_loc")
        if inv_f and loc_f:
            if st.button("🔍 Run Audit"):
                df_inv = pd.read_csv(inv_f) if inv_f.name.endswith('.csv') else pd.read_excel(inv_f)
                df_loc = pd.read_csv(loc_f) if loc_f.name.endswith('.csv') else pd.read_excel(loc_f)
                df_inv['compare_key'] = df_inv.apply(lambda r: f"{advanced_normalize(r['Name'])}__{advanced_normalize(r['Artist'])}__{advanced_normalize(r['Album'])}", axis=1)
                loc_keys = {f"{advanced_normalize(str(e).split(',')[0])}__{advanced_normalize(str(e).split(',')[1])}__{advanced_normalize(str(e).split(',')[2])}" for e in df_loc.iloc[:, 0] if len(str(e).split(',')) >= 3}
                missing_df = df_inv[~df_inv['compare_key'].isin(loc_keys)].copy()
                st.balloons()
                st.dataframe(missing_df[['Original Pos', 'Name', 'Artist', 'Album']], use_container_width=True, hide_index=True)
                st.download_button("📥 Download Missing List", missing_df.to_csv(index=False).encode('utf-8'), f"{safe_proj}_Missing.csv", "text/csv")

    elif choice == "📊 Collection Reviewer":
        st.title(f"📊 Collection Reviewer: {st.session_state['global_proj']}")
        c1, c2 = st.columns(2)
        with c1: inv_f = st.file_uploader("Inventory", type=["csv", "xlsx"], key="rev_inv")
        with c2: loc_f = st.file_uploader("Local Library", type=["csv", "xlsx"], key="rev_loc")
        if inv_f and loc_f:
            if st.button("📊 Generate Smart Review"):
                df_inv = pd.read_csv(inv_f) if inv_f.name.endswith('.csv') else pd.read_excel(inv_f)
                df_loc = pd.read_csv(loc_f) if loc_f.name.endswith('.csv') else pd.read_excel(loc_f)
                inv_rows = [{'Source': 'Spotify', 'Name': r['Name'], 'Artist': r['Artist'], 'Album': r['Album'], 'Key': f"{advanced_normalize(r['Name'])}__{advanced_normalize(r['Artist'])}__{advanced_normalize(r['Album'])}"} for _, r in df_inv.iterrows()]
                loc_rows = []
                for e in df_loc.iloc[:, 0]:
                    p = str(e).split(',')
                    if len(p) >= 3: loc_rows.append({'Source': 'Local MP3', 'Name': p[0], 'Artist': p[1], 'Album': p[2], 'Key': f"{advanced_normalize(p[0])}__{advanced_normalize(p[1])}__{advanced_normalize(p[2])}"})
                master_df = pd.concat([pd.DataFrame(inv_rows), pd.DataFrame(loc_rows)]).sort_values(by=['Key', 'Source']).reset_index(drop=True)
                master_df.insert(0, 'Ref Row', master_df.index + 1)
                counts = master_df['Key'].value_counts()
                lone_wolf_keys = counts[counts == 1].index.tolist()
                st.write("---")
                c1, c2, c3 = st.columns(3)
                c1.metric("Tracks", len(master_df))
                c2.metric("Mismatches", len(lone_wolf_keys), delta_color="inverse")
                c3.metric("Match Rate", f"{((len(master_df) - len(lone_wolf_keys)) / len(master_df)) * 100:.1f}%" if len(master_df) > 0 else "0%")
                def style_wolf(data):
                    s = pd.DataFrame('', index=data.index, columns=data.columns)
                    s.loc[data['Key'].isin(lone_wolf_keys), :] = 'background-color: #ffcccc'
                    return s
                st.balloons()
                st.dataframe(master_df.style.apply(style_wolf, axis=None), use_container_width=True, hide_index=True)
                st.download_button("📥 Download Report", master_df.to_csv(index=False).encode('utf-8'), f"{safe_proj}_Health.csv", "text/csv")

    elif choice == "🗑️ Playlist Deleter":
        st.title("🗑️ Spotify Playlist Deleter")
        if not token_info: st.warning("Connect Spotify first.")
        else:
            sp_write = spotipy.Spotify(auth_manager=auth_manager)
            if st.button("🔍 Load My Playlists"):
                st.session_state['my_playlists'] = sp_write.current_user_playlists(limit=50)['items']
            if 'my_playlists' in st.session_state:
                with st.form("delete_form"):
                    to_delete = []
                    for p in st.session_state['my_playlists']:
                        label = f"{p['name']} (ID: {p['id']}) — {p['tracks']['total']} tracks"
                        if st.checkbox(label, key=p['id']): to_delete.append(p['id'])
                    if st.form_submit_button("🔥 DELETE SELECTED"):
                        for pid in to_delete: sp_write.current_user_unfollow_playlist(pid)
                        st.success(f"Deleted {len(to_delete)} playlists."); del st.session_state['my_playlists']; st.rerun()

    # --- 7. NEW TOOL: SIDECAR SCRAPER ---
    elif choice == "🕵️ Sidecar Scraper":
        st.title("🕵️ Sidecar Musical Scraper")
        st.info("Bypasses Spotify API. Upload your Inventory CSV to find musical Keys and BPM via Tunebat.")
        
        inv_f = st.file_uploader("Upload Spotify Inventory (CSV)", type="csv")
        if inv_f:
            df_inv = pd.read_csv(inv_f)
            if st.button("🚀 Start Web Scrape"):
                results = []
                progress_bar = st.progress(0)
                total = len(df_inv)
                
                for i, row in df_inv.iterrows():
                    name, artist = row['Name'], row['Artist']
                    st.write(f"Hunting: {name} by {artist}...")
                    key, bpm = scrape_key_bpm(name, artist)
                    results.append({'Name': name, 'Artist': artist, 'Key': key, 'BPM': bpm})
                    progress_bar.progress((i + 1) / total)
                    time.sleep(0.5) # Sleep to avoid rate limiting
                
                df_scraped = pd.DataFrame(results)
                st.success("Scrape Complete!")
                st.dataframe(df_scraped, use_container_width=True, hide_index=True)
                st.download_button("📥 Download Scraped DNA (CSV)", df_scraped.to_csv(index=False).encode('utf-8'), f"{safe_proj}_Scraped_DNA.csv", "text/csv")

# --- FINAL FOOTER ---
st.write("---")
cur_p = st.session_state.get('global_proj', 'Default')
st.caption(f"AfexCloud Dashboard | Project: {cur_p if cur_p else 'Default'} | v2.7 deployment")
