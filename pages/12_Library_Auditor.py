import streamlit as st
import pandas as pd
import gspread
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from google.oauth2.service_account import Credentials
from afexcloud.layout import bootstrap_page

# 1. Page Config
st.set_page_config(page_title="Library Auditor | AfexCloud", page_icon="🪞", layout="wide")
bootstrap_page()

st.title("🪞 Afex Library Auditor")
st.caption("Zero-File Workflow | Spotify & GSheets Integrated | Evans/Greeley HQ")

# 2. Connection Handshakes
def get_gspread_client():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(st.secrets["google_gsheets"], scopes=scope)
    return gspread.authorize(creds)

def get_spotify_client():
    # Use existing secrets 
    auth_manager = SpotifyClientCredentials(
        client_id=st.secrets["SPOTIFY_CLIENT_ID"],
        client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"]
    )
    return spotipy.Spotify(auth_manager=auth_manager)

# 3. Step 1: Define the "Target" (Client Playlist)
st.subheader("📡 Step 1: Connect Client Playlist")
target_source = st.radio("Fetch Client Tracks From:", ["Direct Spotify Link (Recommended)", "Client Google Sheet", "Manual CSV"])

target_df = None

if target_source == "Direct Spotify Link (Recommended)":
    playlist_url = st.text_input("Paste Spotify Playlist URL:", placeholder="https://open.spotify.com/playlist/...")
    if playlist_url:
        try:
            sp = get_spotify_client()
            playlist_id = playlist_url.split('/')[-1].split('?')[0]
            results = sp.playlist_items(playlist_id)
            tracks = []
            for item in results['items']:
                track = item['track']
                tracks.append({"Name": track['name'], "Artist": track['artists'][0]['name'], "Album": track['album']['name']})
            target_df = pd.DataFrame(tracks)
            st.success(f"Harvested {len(target_df)} tracks directly from Spotify!")
        except Exception as e:
            st.error(f"Spotify Harvest Failed: {e}")

elif target_source == "Client Google Sheet":
    client_sheet_url = st.text_input("Paste Client Google Sheet URL:")
    if client_sheet_url:
        try:
            client = get_gspread_client()
            sheet = client.open_by_url(client_sheet_url.split('/edit')[0]).get_worksheet(0)
            target_df = pd.DataFrame(sheet.get_all_records())
            st.success(f"Pulled {len(target_df)} tracks from Client Sheet!")
        except Exception as e:
            st.error(f"Client Sheet Connection Failed: {e}")

# 4. Step 2: Connect the "Inventory" (Master Cloud Sheet)
st.write("---")
st.subheader("📦 Step 2: Connect Master Inventory")
master_inv_url = st.text_input("Master Inventory Google Sheet URL:", 
                               value="https://docs.google.com/spreadsheets/d/1lHZm2gniKaODA60T50oHnMWl-ajZGJ1jkNUtm7TbHbs")

inventory_df = None
if master_inv_url:
    try:
        client = get_gspread_client()
        sheet = client.open_by_url(master_inv_url.split('/edit')[0]).get_worksheet(0)
        inventory_df = pd.DataFrame(sheet.get_all_records())
        st.success(f"Inventory Synced: {len(inventory_df)} tracks ready.")
    except Exception as e:
        st.error(f"Inventory Connection Failed: {e}")

# 5. Step 3: Execute Audit
if target_df is not None and inventory_df is not None:
    st.write("---")
    st.subheader("🔍 Step 3: Audit Results")
    
    # Matching Logic
    target_df['Match_Key'] = target_df['Name'].str.lower().str.strip() + " " + target_df['Artist'].str.lower().str.strip()
    inventory_df['Match_Key'] = inventory_df['Name'].str.lower().str.strip() + " " + inventory_df['Artist'].str.lower().str.strip()
    
    missing = target_df[~target_df['Match_Key'].isin(inventory_df['Match_Key'])]
    found = target_df[target_df['Match_Key'].isin(inventory_df['Match_Key'])]
    
    # Display Results
    colA, colB = st.columns(2)
    colA.metric("Total in Request", len(target_df))
    colB.metric("Gaps Found", len(missing))
    
    tab1, tab2 = st.tabs(["❌ Gaps (Need to Acquire)", "✅ Found (Ready to Play)"])
    with tab1:
        st.dataframe(missing[['Name', 'Artist', 'Album']], use_container_width=True, hide_index=True)
    with tab2:
        # Show Heritage Data so OGs can confirm 
        results_df = inventory_df[inventory_df['Match_Key'].isin(found['Match_Key'])]
        st.dataframe(results_df[['Name', 'Artist', 'Original_Name', 'Original_Artist', 'Full Path']], use_container_width=True, hide_index=True)
