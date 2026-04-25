import streamlit as st
import pandas as pd
import gspread
import spotipy
import os
from spotipy.oauth2 import SpotifyClientCredentials
from google.oauth2.service_account import Credentials
from afexcloud.layout import bootstrap_page

# 1. Page Config
st.set_page_config(page_title="Gap Mirror | AfexCloud", page_icon="🪞", layout="wide")
bootstrap_page()

st.title("🪞 Afex Gap Mirror (Cloud Edition)")
st.caption("Zero-File Workflow | Spotify & GSheets Integrated | Evans/Greeley HQ")

# 2. Handshake Engines
def get_gspread_client():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    info = dict(st.secrets["google_gsheets"])
    info["private_key"] = info["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(info, scopes=scope)
    return gspread.authorize(creds)

def get_spotify_client():
    # DIAGNOSTIC CHECK: Ensure secrets exist
    client_id = st.secrets.get("SPOTIFY_CLIENT_ID")
    client_secret = st.secrets.get("SPOTIFY_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        st.error("🚨 **Spotify Credentials Missing**: Check your Streamlit Secrets.")
        return None
        
    return spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=client_id,
        client_secret=client_secret
    ))

# 3. Step 1: Target Selection (The Request List)
st.subheader("📡 Step 1: Identify Client Requests")
target_mode = st.radio("How are we getting the client list?", ["Direct Spotify Link", "Client Google Sheet", "CSV Upload"])

target_df = None
if target_mode == "Direct Spotify Link":
    p_url = st.text_input("Paste Spotify Playlist URL:", placeholder="https://open.spotify.com/playlist/...")
    
    # ⚠️ REMINDER FOR NEWBIES
    st.info("💡 **Note for DJs**: Ensure the Client's playlist is set to **'Public'**. Private playlists will trigger a 401 error.")

    if p_url and st.button("🚀 Harvest Tracks"):
        try:
            sp = get_spotify_client()
            if sp:
                # Precision Parser for URL
                p_id = p_url.split('/')[-1].split('?')[0]
                results = sp.playlist_items(p_id)
                target_df = pd.DataFrame([{"Name": i['track']['name'], "Artist": i['track']['artists'][0]['name']} for i in results['items']])
                st.success(f"Harvested {len(target_df)} tracks from Spotify.")
        except Exception as e:
            # Handle the 401 specifically
            if "401" in str(e):
                st.error("🚨 **Spotify Auth Failed (401)**: This is likely due to incorrect Client ID/Secret or the playlist being **Private**.")
            else:
                st.error(f"Spotify Error: {e}")

# ... (Rest of the Step 2 and Step 3 logic remains the same)
