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
    @st.cache_resource
    def get_read_client():
        return spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=st.secrets["SPOTIFY_CLIENT_ID"],
            client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"]
        ))

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

    sp_read = get_read_client()
    auth_manager = get_auth_manager()

    # --- 3. AUTO-CAPTURE HANDSHAKE ---
    if "code" in st.query_params:
        try:
            code = st.query_params.get("code")
            auth_manager.get_access_token(code, as_dict=False)
            st.query_params.clear()
            st.success("✅ Spotify Connection Verified!")
        except Exception:
            st.query_params.clear()

    # --- 4. ADVANCED NORMALIZATION (For Accents & Global Clients) ---
    def advanced_normalize(text):
        """Standardizes text and handles Mojibake encoding issues."""
        if not isinstance(text, str): 
            text = str(text)
        
        # Try to fix common encoding errors (Mojibake)
        try:
            text = text.encode('cp1252').decode('utf-8')
        except:
            pass 
        
        # Strip accents (diacritics)
        text = unicodedata.normalize('NFKD', text)
        text = "".join([c for c in text if not unicodedata.combining(c)])
        
        # Clean special chars, lowercase, and trim
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s]', '', text)
        return re.sub(r'\s+', ' ', text).strip()

    def get_all_tracks_with_pos(playlist_id):
        tracks = []
        try:
            results = sp_read.playlist_tracks(playlist_id)
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
        except Exception as e:
            st.error(f"Spotify API Error: {e}")
            return []
        return tracks

    # --- 5. SIDEBAR NAVIGATION ---
    with st.sidebar:
        st.title("☁️ AfexCloud")
        choice = st.radio("Select a Tool:", 
            ["🏠 Home", "🔍 Duplicate Finder", "📋 Song Lister", "📦 Batch Manager", "💿 Library Auditor"])
        if st.button("🚪 Log Out"):
            st.session_state["password_correct"] = False
            st.rerun()

    # --- 6. DASHBOARD PAGES ---
    
    if choice == "🏠 Home":
        st.title("🚀 AfexCloud Marketing Dashboard")
        st.info("The multi-tool suite is fully operational. Select a tool from the sidebar to begin.")

    elif choice == "🔍 Duplicate Finder":
        st.title("🔍 Spotify Duplicate Finder")
        url = st.text_input("Enter Playlist URL/ID:")
        if st.button("Run Duplicate Scan"):
            p_id = url.split('/')[-1].split('?')[0] if '/' in url else url
            tracks = get_all_tracks_with_pos(p_id)
            if tracks:
                by_id = defaultdict(list)
                for t in tracks: by_id[t['Spotify - id']].append(t)
                dupes = [i for g in by_id.values() if len(g) > 1 for i in g]
                if dupes:
                    st.warning(f"Found {len(dupes)} duplicates.")
                    st.dataframe(pd.DataFrame(dupes), use_container_width=True, hide_index=True)
                else:
                    st.success("No duplicates found!")

    elif choice == "📋 Song Lister":
        st.title("📋 Playlist Inventory Lister")
        url = st.text_input("Enter Playlist URL/ID:")
        if st.button("Generate Inventory"):
            p_id = url.split('/')[-1].split('?')[0] if '/' in url else url
            tracks = get_all_tracks_with_pos(p_id)
            if tracks:
                df = pd.DataFrame(tracks)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.download_button("📥 Download Inventory (CSV)", df.to_csv(index=False).encode('utf-8'), "inventory.csv", "text/csv")

    # --- 6. BATCH MANAGER (Full Logic Restored) ---
    elif choice == "📦 Batch Manager":
        st.title("📦 Batch Management Tool")
        tab1, tab2 = st.tabs(["Step 1: Create CSV Batches", "Step 2: Upload to Spotify"])

        with tab1:
            st.subheader("1. Split Playlist into Batches of 25")
            url = st.text_input("Source Playlist URL/ID:", key="batch_source_input")
            if st.button("Generate Batches"):
                p_id = url.split('/')[-1].split('?')[0] if '/' in url else url
                all_tracks = get_all_tracks_with_pos(p_id)
                if all_tracks:
                    num_batches = ceil(len(all_tracks) / 25)
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w") as zf:
                        for i in range(num_batches):
                            batch = all_tracks[i*25 : (i+1)*25]
                            df_batch = pd.DataFrame(batch)[['Original Pos', 'Name', 'Artist', 'Album', 'Spotify - id']]
                            range_label = f"{batch[0]['Original Pos']}_to_{batch[-1]['Original Pos']}"
                            csv_name = f"Batch_{i+1}_Tracks_{range_label}.csv"
                            zf.writestr(csv_name, df_batch.to_csv(index=False).encode('utf-8'))
                            with st.expander(f"View Batch {i+1} (Tracks {range_label})"):
                                st.dataframe(df_batch, use_container_width=True, hide_index=True)

                    st.write("---")
                    st.download_button("📦 DOWNLOAD ALL BATCHES (ZIP)", zip_buffer.getvalue(), "all_batches.zip", "application/zip", type="primary")

        with tab2:
            st.subheader("2. Upload Batches to Spotify")
            token_info = auth_manager.validate_token(auth_manager.cache_handler.get_cached_token())
            if not token_info:
                st.warning("🔑 Authorization Required")
                st.markdown(f"[Click Here to Authorize Spotify]({auth_manager.get_authorize_url()})")
                manual_url = st.text_input("Paste Redirect URL here if needed:")
                if st.button("Complete Connection"):
                    auth_manager.get_access_token(auth_manager.parse_response_code(manual_url), as_dict=False)
                    st.rerun()
            else:
                st.success("✅ Spotify Connected")
                uploaded_files = st.file_uploader("Upload Batch CSVs", accept_multiple_files=True, type="csv")
                if st.button("🚀 Create Spotify Playlists", type="primary"):
                    if uploaded_files:
                        sp_write = spotipy.Spotify(auth_manager=auth_manager)
                        user_id = sp_write.current_user()['id']
                        report_data = []
                        start_t = time.time()
                        with st.status("Uploading...") as status:
                            for f in uploaded_files:
                                try:
                                    df = pd.read_csv(f)
                                    if 'Spotify - id' in df.columns:
                                        p = sp_write.user_playlist_create(user=user_id, name=f"Batch: {f.name}", public=False)
                                        uris = [f"spotify:track:{tid}" for tid in df['Spotify - id'].tolist()]
                                        sp_write.playlist_add_items(p['id'], uris)
                                        report_data.append({"File": f.name, "Songs": len(df), "Status": "✅ Success"})
                                except Exception as e:
                                    report_data.append({"File": f.name, "Songs": 0, "Status": f"❌ Error: {e}"})
                            status.update(label="Complete!", state="complete")
                        st.balloons()
                        st.header("📊 Success Report")
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Playlists", len(report_data))
                        c2.metric("Tracks", sum(d['Songs'] for d in report_data))
                        c3.metric("Time", f"{round(time.time()-start_t, 2)}s")
                        st.table(pd.DataFrame(report_data))

    # --- 7. MST-SYNCHRONIZED LIBRARY AUDITOR (With Search Bar) ---
    elif choice == "💿 Library Auditor":
        st.title("💿 Library Auditor")
        st.info("Compare Spotify Inventory against Local MP3s. Sync: MST.")
        
        c1, c2 = st.columns(2)
        with c1:
            inv_file = st.file_uploader("Upload Spotify Inventory", type="xlsx", key="aud_inv")
        with c2:
            loc_file = st.file_uploader("Upload Local Songs", type="xlsx", key="aud_loc")
            
        if inv_file and loc_file:
            # SEARCH BAR ADDITION
            search_query = st.text_input("🔍 Quick Search (Name, Artist, or Album):")
            
            if st.button("🔍 Run Full Audit"):
                with st.spinner("Analyzing song collections..."):
                    from datetime import datetime, timedelta
                    mst_now = datetime.utcnow() - timedelta(hours=7)
                    run_time_str = mst_now.strftime("%Y-%m-%d %H:%M:%S")

                    inv_df = pd.read_excel(inv_file)
                    loc_df = pd.read_excel(loc_file)
                    
                    inv_df['compare_key'] = inv_df.apply(lambda r: 
                        f"{advanced_normalize(r['Name'])}__{advanced_normalize(r['Artist'])}__{advanced_normalize(r['Album'])}", axis=1)
                    
                    local_keys = set()
                    for entry in loc_df.iloc[:, 0]:
                        parts = str(entry).split(',') 
                        if len(parts) >= 3:
                            k = f"{advanced_normalize(parts[0])}__{advanced_normalize(parts[1])}__{advanced_normalize(parts[2])}"
                            local_keys.add(k)
                    
                    missing_df = inv_df[~inv_df['compare_key'].isin(local_keys)].copy()
                    
                    # Apply Search Filter if query exists
                    if search_query:
                        q = search_query.lower()
                        missing_df = missing_df[
                            missing_df['Name'].str.lower().contains(q, na=False) | 
                            missing_df['Artist'].str.lower().contains(q, na=False) |
                            missing_df['Album'].str.lower().contains(q, na=False)
                        ]

                    st.write("---")
                    st.balloons()
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Local Library Size", len(local_keys))
                    m2.metric("Missing Songs", len(missing_df))
                    m3.metric("MST Run Time", mst_now.strftime("%H:%M:%S"))
                    
                    if not missing_df.empty:
                        st.subheader(f"🛒 Missing Songs List (Run: {run_time_str} MST)")
                        display_cols = ['Original Pos', 'Name', 'Artist', 'Album']
                        st.dataframe(missing_df[display_cols], use_container_width=True, hide_index=True)
                        st.download_button(
                            label=f"📥 Download Report", 
                            data=missing_df[display_cols].to_csv(index=False).encode('utf-8'), 
                            file_name=f"Audit_{mst_now.strftime('%H%M%S')}_MST.csv", 
                            mime="text/csv"
                        )
                    else:
                        st.success(f"🎉 100% Match! (Verified at {run_time_str} MST)")

# --- FINAL FOOTER (Outside all blocks) ---
st.write("---")
st.caption("AfexCloud Suite | Batch & Audit Restored | MST Timezone")

# --- FINAL FOOTER (Ensure these two lines are at the very bottom and NOT indented) ---
st.write("---")
st.caption("AfexCloud Suite | Audit & Batch Enabled | MST Timezone Active")

