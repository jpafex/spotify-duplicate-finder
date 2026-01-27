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
from collections import defaultdict
from datetime import datetime, timedelta

# Page config
st.set_page_config(page_title="AfexCloud Dashboard", page_icon="☁️", layout="wide")

# --- 1. SECURE LOGIN GATE ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 AfexCloud Tool Login")
        with st.form("login_form"):
            user_input = st.text_input("Username")
            pass_input = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            if submit:
                if user_input == st.secrets["APP_USER"] and pass_input == st.secrets["APP_PASS"]:
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
        return False
    return st.session_state.get("password_correct", True)

if check_password():
    
    # --- 2. AUTHENTICATION ENGINES ---
    def get_auth_manager():
        scope = "playlist-modify-public playlist-modify-private"
        return SpotifyOAuth(
            client_id=st.secrets["SPOTIFY_CLIENT_ID"],
            client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"],
            redirect_uri=st.secrets["SPOTIFY_REDIRECT_URI"],
            scope=scope,
            open_browser=False,
            cache_path=".cache-token"
        )

    auth_manager = get_auth_manager()

    # --- 3. GLOBAL CONNECTION CHECK ---
    token_info = auth_manager.validate_token(auth_manager.cache_handler.get_cached_token())
    if "code" in st.query_params and not token_info:
        try:
            code = st.query_params.get("code")
            auth_manager.get_access_token(code, as_dict=False)
            st.query_params.clear()
            st.rerun() 
        except Exception:
            st.query_params.clear()

    # --- 4. ADVANCED HELPERS ---
    def advanced_normalize(text):
        if not isinstance(text, str): text = str(text)
        try:
            text = text.encode('cp1252').decode('utf-8')
        except:
            pass
        text = unicodedata.normalize('NFKD', text)
        text = "".join([c for c in text if not unicodedata.combining(c)])
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s]', '', text)
        return re.sub(r'\s+', ' ', text).strip()

    def get_playlist_metadata(url_or_id):
        """Fetches both Name and Tracks from Spotify."""
        sp_read = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=st.secrets["SPOTIFY_CLIENT_ID"],
            client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"]
        ))
        p_id = url_or_id.split('/')[-1].split('?')[0] if '/' in url_or_id else url_or_id
        try:
            # Get Playlist Metadata
            meta = sp_read.playlist(p_id, fields="name")
            p_name = meta['name']
            
            # Get Tracks
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
            return "Unknown_Playlist", []

    # --- 5. SIDEBAR (Global Project Name) ---
    with st.sidebar:
        st.title("☁️ AfexCloud")
        
        # New: Global Project Field (Applied to all tools)
        st.write("---")
        global_proj = st.text_input("📁 Global Project / Client Name:", 
                                     placeholder="e.g. AN_Construction_Jan_Audit")
        st.write("---")

        if token_info:
            st.success("🟢 Spotify: Connected")
        else:
            st.error("🔴 Spotify: Not Connected")
            st.markdown(f"[**Connect Spotify**]({auth_manager.get_authorize_url()})")

        choice = st.radio("Select a Tool:", 
            ["🏠 Home", "🔍 Duplicate Finder", "📋 Song Lister", "📦 Batch Manager", "💿 Library Auditor", "📊 Collection Reviewer"])
        
        st.write("---")
        if st.button("🚪 Log Out"):
            st.session_state["password_correct"] = False
            st.rerun()

    # Clean Project Prefix for Filenames
    safe_proj = re.sub(r'[^a-zA-Z0-9_]', '_', global_proj) if global_proj else ""
    
    # --- 6. TOOLS ---
    
    if choice == "🏠 Home":
        st.title("🚀 AfexCloud Marketing Dashboard")
        st.info(f"Active Project: **{global_proj if global_proj else 'None Set'}**")
        st.write("Use the sidebar to manage duplicates, batches, and library audits.")

    elif choice == "🔍 Duplicate Finder":
        st.title(f"🔍 Duplicate Finder: {global_proj}")
        url = st.text_input("Playlist URL/ID:")
        if st.button("Run Scan"):
            p_name, tracks = get_playlist_metadata(url)
            if tracks:
                by_id = defaultdict(list)
                for t in tracks: by_id[t['Spotify - id']].append(t)
                dupes = [i for g in by_id.values() if len(g) > 1 for i in g]
                if dupes:
                    df_dupes = pd.DataFrame(dupes)
                    st.warning(f"Found {len(dupes)} duplicates in '{p_name}'.")
                    st.dataframe(df_dupes, use_container_width=True, hide_index=True)
                    f_name = f"{safe_proj}_Dupes_{p_name}.csv" if safe_proj else f"Dupes_{p_name}.csv"
                    st.download_button("📥 Download Dupes", df_dupes.to_csv(index=False).encode('utf-8'), f_name, "text/csv")
                else:
                    st.success(f"No duplicates in '{p_name}'!")

    elif choice == "📋 Song Lister":
        st.title(f"📋 Song Lister: {global_proj}")
        url = st.text_input("Playlist URL/ID:")
        if st.button("Generate Inventory"):
            p_name, tracks = get_playlist_metadata(url)
            if tracks:
                df = pd.DataFrame(tracks)
                st.dataframe(df, use_container_width=True, hide_index=True)
                f_name = f"{safe_proj}_Inventory_{p_name}.csv" if safe_proj else f"Inventory_{p_name}.csv"
                st.download_button("📥 Download Inventory (CSV)", df.to_csv(index=False).encode('utf-8'), f_name, "text/csv")

    elif choice == "📦 Batch Manager":
        st.title(f"📦 Batch Manager: {global_proj}")
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
                            range_label = f"{batch[0]['Original Pos']}_to_{batch[-1]['Original Pos']}"
                            # Intelligent Naming: [Project]_[Playlist]_Batch_X
                            csv_name = f"{safe_proj + '_' if safe_proj else ''}{clean_p_name}_Batch_{i+1}_{range_label}.csv"
                            zf.writestr(csv_name, df_batch.to_csv(index=False).encode('utf-8'))
                    st.download_button(f"📦 DOWNLOAD ZIP ({p_name})", zip_buffer.getvalue(), f"Batches_{clean_p_name}.zip", "application/zip")
        with tab2:
            st.subheader("2. Upload to Spotify")
            if not token_info: st.warning("Connect Spotify first.")
            else:
                files = st.file_uploader("Upload CSVs", accept_multiple_files=True, type="csv")
                if st.button("🚀 Create Playlists"):
                    sp_write = spotipy.Spotify(auth_manager=auth_manager)
                    for f in files:
                        df = pd.read_csv(f)
                        p = sp_write.user_playlist_create(user=sp_write.current_user()['id'], name=f"{global_proj if global_proj else 'Batch'}: {f.name}", public=False)
                        sp_write.playlist_add_items(p['id'], [f"spotify:track:{tid}" for tid in df['Spotify - id'].tolist()])
                    st.balloons()

    elif choice == "💿 Library Auditor":
        st.title(f"💿 Library Auditor: {global_proj}")
        c1, c2 = st.columns(2)
        with c1: inv_f = st.file_uploader("Spotify Inventory (CSV/XLSX)", type=["csv", "xlsx"], key="aud_inv")
        with c2: loc_f = st.file_uploader("Local Songs (CSV/XLSX)", type=["csv", "xlsx"], key="aud_loc")
        if inv_f and loc_f:
            if st.button("🔍 Run Audit"):
                df_inv = pd.read_csv(inv_f) if inv_f.name.endswith('.csv') else pd.read_excel(inv_f)
                df_loc = pd.read_csv(loc_f) if loc_f.name.endswith('.csv') else pd.read_excel(loc_f)
                df_inv['compare_key'] = df_inv.apply(lambda r: f"{advanced_normalize(r['Name'])}__{advanced_normalize(r['Artist'])}__{advanced_normalize(r['Album'])}", axis=1)
                loc_keys = {f"{advanced_normalize(str(e).split(',')[0])}__{advanced_normalize(str(e).split(',')[1])}__{advanced_normalize(str(e).split(',')[2])}" for e in df_loc.iloc[:, 0] if len(str(e).split(',')) >= 3}
                missing_df = df_inv[~df_inv['compare_key'].isin(loc_keys)].copy()
                st.balloons()
                st.subheader(f"Missing tracks for project: {global_proj}")
                st.dataframe(missing_df[['Original Pos', 'Name', 'Artist', 'Album']], use_container_width=True, hide_index=True)
                f_name = f"{safe_proj}_Missing_Audit.csv" if safe_proj else "missing_audit.csv"
                st.download_button("📥 Download Missing List", missing_df.to_csv(index=False).encode('utf-8'), f_name, "text/csv")

    elif choice == "📊 Collection Reviewer":
        st.title(f"📊 Collection Reviewer: {global_proj}")
        c1, c2 = st.columns(2)
        with c1: inv_f = st.file_uploader("Spotify Inventory", type=["csv", "xlsx"], key="rev_inv")
        with c2: loc_f = st.file_uploader("Local Songs", type=["csv", "xlsx"], key="rev_loc")
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
                st.subheader(f"📊 Production Health: {global_proj}")
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
                f_name = f"{safe_proj}_Health_Report.csv" if safe_proj else "Health_Report.csv"
                st.download_button("📥 Download Report", master_df.to_csv(index=False).encode('utf-8'), f_name, "text/csv")

# --- FINAL FOOTER ---
st.write("---")
st.caption(f"AfexCloud Dashboard | Project: {global_proj if global_proj else 'Default'} | MST Active")
