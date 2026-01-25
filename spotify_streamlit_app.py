import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from collections import defaultdict
import pandas as pd

# Page config
st.set_page_config(page_title="AfexCloud Dashboard", page_icon="☁️", layout="wide")

# --- 1. SECURE LOGIN GATE ---
def check_password():
    def password_entered():
        if (
            st.session_state["username"] == st.secrets["APP_USER"]
            and st.session_state["password"] == st.secrets["APP_PASS"]
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔐 AfexCloud Tool Login")
        st.text_input("Username", on_change=password_entered, key="username")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔐 AfexCloud Tool Login")
        st.text_input("Username", on_change=password_entered, key="username")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("Invalid credentials.")
        return False
    return True

# --- 2. SHARED DATA ENGINE ---
if check_password():
    
    # Spotify API Setup
    @st.cache_resource
    def get_spotify_client():
        return spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=st.secrets["SPOTIFY_CLIENT_ID"],
            client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"]
        ))

    sp = get_spotify_client()

    def get_playlist_tracks(playlist_id):
        tracks = []
        try:
            results = sp.playlist_tracks(playlist_id)
            while results:
                for item in results['items']:
                    if item.get('track'):
                        t = item['track']
                        tracks.append({
                            'id': t.get('id'),
                            'name': t.get('name', 'Unknown'),
                            'artist': t['artists'][0]['name'] if t.get('artists') else 'Unknown',
                            'album': t['album']['name'] if t.get('album') else 'Unknown',
                        })
                results = sp.next(results) if results['next'] else None
        except Exception as e:
            st.error(f"Spotify Error: {e}")
            return []
        return tracks

    # --- 3. SIDEBAR NAVIGATION ---
    with st.sidebar:
        st.title("☁️ AfexCloud")
        st.write(f"Logged in as: **{st.secrets['APP_USER']}**")
        st.write("---")
        
        # Dashboard Menu
        choice = st.radio(
            "Select a Tool:",
            ["🏠 Dashboard Home", "🔍 Duplicate Finder", "📋 Song Lister (Full Inventory)"]
        )
        
        st.write("---")
        if st.button("🔄 Global Refresh"):
            st.cache_resource.clear()
            st.rerun()
        
        if st.button("🚪 Log Out"):
            st.session_state["password_correct"] = False
            st.rerun()

    # --- 4. DASHBOARD PAGES ---

    # --- PAGE: HOME ---
    if choice == "🏠 Dashboard Home":
        st.title("🚀 AfexCloud Marketing Dashboard")
        st.write("Welcome to your private tool suite. Select a tool from the sidebar to get started.")
        
        col_h1, col_h2 = st.columns(2)
        with col_h1:
            st.info("### 🔍 Duplicate Finder\nClean up playlists by identifying exact and similar tracks.")
        with col_h2:
            st.info("### 📋 Song Lister\nGenerate a complete inventory of any public Spotify playlist.")

    # --- PAGE: DUPLICATE FINDER ---
    elif choice == "🔍 Duplicate Finder":
        st.title("🔍 Spotify Duplicate Finder")
        url = st.text_input("Enter Playlist URL/ID:", key="dup_input")
        
        if st.button("Run Analysis", type="primary"):
            p_id = url.split('/')[-1].split('?')[0] if '/' in url else url
            with st.spinner("Analyzing..."):
                tracks = get_playlist_tracks(p_id)
                if tracks:
                    # Logic for finding duplicates
                    by_id = defaultdict(list)
                    by_name = defaultdict(list)
                    for i, t in enumerate(tracks):
                        pos = i + 1
                        if t['id']: by_id[t['id']].append({**t, 'pos': pos})
                        key = f"{t['name'].lower()}::{t['artist'].lower()}"
                        by_name[key].append({**t, 'pos': pos})
                    
                    exact = {k: v for k, v in by_id.items() if len(v) > 1}
                    similar = {k: v for k, v in by_name.items() if len(v) > 1}
                    
                    # Consolidate for display
                    dupe_data = []
                    for tid, dupes in exact.items():
                        for d in dupes: dupe_data.append({**d, 'Match': 'Exact'})
                    for key, dupes in similar.items():
                        for d in dupes:
                            if not any(x['id'] == d['id'] and x['pos'] == d['pos'] for x in dupe_data):
                                dupe_data.append({**d, 'Match': 'Similar'})

                    if not dupe_data:
                        st.success("No duplicates found!")
                    else:
                        df = pd.DataFrame(dupe_data)[['pos', 'name', 'artist', 'album', 'Match', 'id']]
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        st.download_button("📊 Export Duplicates (CSV)", df.to_csv(index=False), "dupes.csv", "text/csv")

    # --- PAGE: SONG LISTER ---
    elif choice == "📋 Song Lister (Full Inventory)":
        st.title("📋 Playlist Inventory Lister")
        st.write("Generate a numbered list of all tracks in a playlist.")
        url = st.text_input("Enter Playlist URL/ID:", key="list_input")
        
        if st.button("Generate List", type="primary"):
            p_id = url.split('/')[-1].split('?')[0] if '/' in url else url
            with st.spinner("Fetching tracks..."):
                tracks = get_playlist_tracks(p_id)
                if tracks:
                    # Create the inventory DataFrame
                    inv_data = []
                    for i, t in enumerate(tracks):
                        inv_data.append({
                            'Pos': i + 1,
                            'Song Title': t['name'],
                            'Artist': t['artist'],
                            'Album': t['album'],
                            'Spotify ID': t['id']
                        })
                    
                    df_inv = pd.DataFrame(inv_data)
                    
                    # Display metrics
                    st.metric("Total Songs Found", len(tracks))
                    
                    # Display Data Preview
                    st.write("### 📜 Playlist Inventory")
                    st.dataframe(df_inv, use_container_width=True, hide_index=True)
                    
                    # Export Options
                    st.write("### 💾 Export Inventory")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.download_button("📊 Download as CSV", df_inv.to_csv(index=False), "playlist_inventory.csv", "text/csv", use_container_width=True)
                    with c2:
                        txt_out = f"PLAYLIST INVENTORY\n{'='*20}\n"
                        for _, r in df_inv.iterrows():
                            txt_out += f"{r['Pos']}. {r['Song Title']} - {r['Artist']} [ID: {r['Spotify ID']}]\n"
                        st.download_button("📥 Download as TXT", txt_out, "playlist_inventory.txt", "text/plain", use_container_width=True)

    st.write("---")
    st.caption("AfexCloud Private Suite | Secured for jpafex")
