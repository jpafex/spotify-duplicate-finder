import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import pandas as pd
from math import ceil
import io
import zipfile
import time
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

    # --- 4. HELPER FUNCTIONS ---
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
        choice = st.radio("Select a Tool:", ["🏠 Home", "🔍 Duplicate Finder", "📋 Song Lister", "📦 Batch Manager"])
        if st.button("🚪 Log Out"):
            st.session_state["password_correct"] = False
            st.rerun()

    # --- 6. DASHBOARD PAGES ---
    
    # PAGE: HOME
    if choice == "🏠 Home":
        st.title("🚀 AfexCloud Marketing Dashboard")
        st.info("The multi-tool suite is fully operational. Select a tool from the sidebar to begin.")
        st.write("Current focus: **High-volume playlist inventory and batch management.**")

    # PAGE: DUPLICATE FINDER
    elif choice == "🔍 Duplicate Finder":
        st.title("🔍 Spotify Duplicate Finder")
        url = st.text_input("Enter Playlist URL/ID:", key="dup_input")
        if st.button("Run Duplicate Scan"):
            p_id = url.split('/')[-1].split('?')[0] if '/' in url else url
            with st.spinner("Scanning for duplicates..."):
                tracks = get_all_tracks_with_pos(p_id)
                if tracks:
                    by_id = defaultdict(list)
                    for t in tracks:
                        by_id[t['Spotify - id']].append(t)
                    
                    dupes = [item for group in by_id.values() if len(group) > 1 for item in group]
                    
                    if not dupes:
                        st.balloons()
                        st.success("🎉 No duplicates found!")
                    else:
                        st.warning(f"Found {len(dupes)} duplicate entries.")
                        df_dupes = pd.DataFrame(dupes)
                        st.dataframe(df_dupes[['Original Pos', 'Name', 'Artist', 'Album', 'Spotify - id']], use_container_width=True, hide_index=True)

    # PAGE: SONG LISTER
    elif choice == "📋 Song Lister":
        st.title("📋 Playlist Inventory Lister")
        url = st.text_input("Enter Playlist URL/ID:", key="list_input")
        if st.button("Generate Inventory List"):
            p_id = url.split('/')[-1].split('?')[0] if '/' in url else url
            with st.spinner("Fetching track list..."):
                tracks = get_all_tracks_with_pos(p_id)
                if tracks:
                    df_list = pd.DataFrame(tracks)
                    st.metric("Total Songs", len(tracks))
                    st.dataframe(df_list, use_container_width=True, hide_index=True)
                    st.download_button("📥 Download Inventory (CSV)", df_list.to_csv(index=False).encode('utf-8'), "inventory.csv", "text/csv")

    # PAGE: BATCH MANAGER
    elif choice == "📦 Batch Manager":
        st.title("📦 Batch Management Tool")
        tab1, tab2 = st.tabs(["Step 1: Create CSV Batches", "Step 2: Upload to Spotify"])

        with tab1:
            st.subheader("1. Split Playlist into Batches of 25")
            url = st.text_input("Source Playlist URL/ID:", key="batch_source")
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
                                        p_name = f"Batch: {f.name}"
                                        p = sp_write.user_playlist_create(user=user_id, name=p_name, public=False)
                                        uris = [f"spotify:track:{tid}" for tid in df['Spotify - id'].tolist()]
                                        sp_write.playlist_add_items(p['id'], uris)
                                        report_data.append({"File": f.name, "Songs": len(df), "Status": "✅ Success"})
                                except Exception as e:
                                    report_data.append({"File": f.name, "Songs": 0, "Status": f"❌ Error: {e}"})
                            status.update(label="Upload Complete!", state="complete")

                        # --- THE SUCCESS REPORT (The Finished Cherry) ---
                        st.balloons()
                        st.header("📊 Batch Upload Success Report")
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Playlists Created", len(report_data))
                        c2.metric("Total Tracks Uploaded", sum(d['Songs'] for d in report_data))
                        c3.metric("Processing Time", f"{round(time.time() - start_t, 2)}s")
                        
                        st.write("### 📜 Execution Log")
                        st.table(pd.DataFrame(report_data))
                    else:
                        st.error("Please upload CSV files first.")

    st.write("---")
    st.caption("AfexCloud Suite | Global Position Tracking & Success Reporting Enabled")
