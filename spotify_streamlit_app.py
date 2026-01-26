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

    # --- 4. ADVANCED NORMALIZATION (The "Gold" Logic) ---
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

    def get_all_tracks_with_pos(playlist_id):
        sp_read = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=st.secrets["SPOTIFY_CLIENT_ID"],
            client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"]
        ))
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
        if token_info:
            st.success("🟢 Spotify: Connected")
        else:
            st.error("🔴 Spotify: Not Connected")
            st.markdown(f"[**Click to Connect**]({auth_manager.get_authorize_url()})")

        choice = st.radio("Select a Tool:", 
            ["🏠 Home", "🔍 Duplicate Finder", "📋 Song Lister", "📦 Batch Manager", "💿 Library Auditor", "📊 Collection Reviewer"])
        
        st.write("---")
        if st.button("🚪 Log Out"):
            st.session_state["password_correct"] = False
            st.rerun()

    # --- 6. TOOLS ---
    
    # [HOME, DUPLICATE FINDER, SONG LISTER, BATCH MANAGER PAGES - UNCHANGED]
    if choice == "🏠 Home":
        st.title("🚀 AfexCloud Marketing Dashboard")
        st.info("The suite is fully operational. New tools added for Library Audit and Visual Review.")

    # ... (Keep existing pages for Duplicate Finder, Song Lister, and Batch Manager) ...

    # --- TOOL: LIBRARY AUDITOR (MISSING ONLY) ---
    elif choice == "💿 Library Auditor":
        st.title("💿 Library Auditor")
        st.info("Identify exactly what needs to be purchased to match your Spotify inventory.")
        # [Keep your existing Auditor logic here]

    # --- 8. COLLECTION REVIEWER (With Reference Rows & Filters) ---
    elif choice == "📊 Collection Reviewer":
        st.title("📊 Collection Reviewer")
        st.info("Visual inspection of song pairs. Lone rows (mismatches) are highlighted in red.")
        
        c1, c2 = st.columns(2)
        with c1:
            inv_f = st.file_uploader("Upload Spotify Inventory", type="xlsx", key="rev_inv")
        with c2:
            loc_f = st.file_uploader("Upload Local Songs", type="xlsx", key="rev_loc")
            
        if inv_f and loc_f:
            # New Filter Toggle
            view_mode = st.radio("Display Mode:", ["Show All Songs", "Show Lone Wolves Only"], horizontal=True)
            
            if st.button("📊 Generate Filtered Review"):
                with st.spinner("Indexing and highlighting..."):
                    # Process Inventory
                    df_inv = pd.read_excel(inv_f)
                    inv_rows = []
                    for _, row in df_inv.iterrows():
                        key = f"{advanced_normalize(row['Name'])}__{advanced_normalize(row['Artist'])}__{advanced_normalize(row['Album'])}"
                        inv_rows.append({'Source': 'Spotify', 'Name': row['Name'], 'Artist': row['Artist'], 'Album': row['Album'], 'Key': key})
                    
                    # Process Local
                    df_loc = pd.read_excel(loc_f)
                    loc_rows = []
                    for entry in df_loc.iloc[:, 0]:
                        parts = str(entry).split(',')
                        if len(parts) >= 3:
                            name, artist, album = parts[0], parts[1], parts[2]
                            key = f"{advanced_normalize(name)}__{advanced_normalize(artist)}__{advanced_normalize(album)}"
                            loc_rows.append({'Source': 'Local MP3', 'Name': name, 'Artist': artist, 'Album': album, 'Key': key})
                    
                    # Combine, Sort, and Reset Index
                    master_df = pd.concat([pd.DataFrame(inv_rows), pd.DataFrame(loc_rows)])
                    master_df = master_df.sort_values(by=['Key', 'Source']).reset_index(drop=True)
                    
                    # ADD REFERENCE ROW (1-based index)
                    master_df.insert(0, 'Ref Row', master_df.index + 1)

                    # Pre-calculate Lone Wolves
                    counts = master_df['Key'].value_counts()
                    lone_wolf_keys = counts[counts == 1].index.tolist()
                    
                    # Filter view if requested
                    if view_mode == "Show Lone Wolves Only":
                        display_df = master_df[master_df['Key'].isin(lone_wolf_keys)].copy()
                    else:
                        display_df = master_df.copy()

                    # Summary Box
                    if lone_wolf_keys:
                        st.error(f"⚠️ Found {len(lone_wolf_keys)} Mismatches (Lone Wolves)")
                        with st.expander("📝 Quick List of Mismatched Titles"):
                            names = master_df[master_df['Key'].isin(lone_wolf_keys)]['Name'].unique()
                            st.write(", ".join(names))
                    else:
                        st.success("🎉 All songs matched perfectly!")

                    # Styling Function
                    def apply_wolf_style(data):
                        style_df = pd.DataFrame('', index=data.index, columns=data.columns)
                        is_lone = data['Key'].isin(lone_wolf_keys)
                        style_df.loc[is_lone, :] = 'background-color: #ffcccc'
                        return style_df

                    st.balloons()
                    st.subheader("🔍 Inspection Table")
                    
                    # Apply styling and display
                    styled_df = display_df.style.apply(apply_wolf_style, axis=None)
                    st.dataframe(styled_df, use_container_width=True, hide_index=True)
                    
                    # Download includes the Ref Row column for Excel lookup
                    st.download_button(
                        label="📥 Download Reference CSV for Excel", 
                        data=display_df.to_csv(index=False).encode('utf-8'), 
                        file_name=f"Collection_Audit_{time.strftime('%H%M%S')}.csv", 
                        mime="text/csv"
                    )

# --- FINAL FOOTER ---
st.write("---")
st.caption("AfexCloud Dashboard | Visual Inspection Tool Active")



