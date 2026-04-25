import streamlit as st
import pandas as pd
import gspread
import spotipy
import traceback
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
    # Uses the secrets we just successfully tested in the Bridge 
    info = dict(st.secrets["google_gsheets"])
    info["private_key"] = info["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(info, scopes=scope)
    return gspread.authorize(creds)

def get_spotify_client():
    return spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=st.secrets["SPOTIFY_CLIENT_ID"],
        client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"]
    ))

# 3. Step 1: Target Selection (The Request List)
st.subheader("📡 Step 1: Identify Client Requests")
target_mode = st.radio("How are we getting the client list?", ["Direct Spotify Link", "Client Google Sheet", "CSV Upload"])

target_df = None
if target_mode == "Direct Spotify Link":
    p_url = st.text_input("Paste Spotify Playlist URL:", placeholder="https://open.spotify.com/playlist/...")
    if p_url and st.button("🚀 Harvest Tracks"):
        try:
            sp = get_spotify_client()
            p_id = p_url.split('/')[-1].split('?')[0]
            results = sp.playlist_items(p_id)
            target_df = pd.DataFrame([{"Name": i['track']['name'], "Artist": i['track']['artists'][0]['name']} for i in results['items']])
            st.success(f"Harvested {len(target_df)} tracks from Spotify.")
        except Exception as e:
            st.error(f"Spotify Error: {e}")

elif target_mode == "Client Google Sheet":
    c_url = st.text_input("Paste Client Sheet URL:")
    if c_url:
        try:
            gc = get_gspread_client()
            sh = gc.open_by_url(c_url.split('/edit')[0]).get_worksheet(0)
            target_df = pd.DataFrame(sh.get_all_records())
            st.success(f"Pulled {len(target_df)} tracks from Google Sheets.")
        except Exception as e:
            st.error(f"GSheet Error: {e}")

# 4. Step 2: Inventory Sync (The Master Cloud)
st.write("---")
st.subheader("📦 Step 2: Sync Master Inventory")
master_url = st.text_input("Master Inventory URL:", value="https://docs.google.com/spreadsheets/d/1lHZm2gniKaODA60T50oHnMWl-ajZGJ1jkNUtm7TbHbs")

inventory_df = None
if master_url:
    try:
        gc = get_gspread_client()
        sh = gc.open_by_url(master_url.split('/edit')[0]).get_worksheet(0)
        inventory_df = pd.DataFrame(sh.get_all_records())
        st.info(f"Inventory Live: {len(inventory_df)} tracks synced.")
    except Exception as e:
        st.error(f"Inventory Error: {e}")

# 5. Step 3: The Audit
if target_df is not None and inventory_df is not None:
    st.write("---")
    st.subheader("🔍 Step 3: Audit Results")
    
    # Matching Engine
    target_df['Match_Key'] = target_df['Name'].str.lower().str.strip() + " " + target_df['Artist'].str.lower().str.strip()
    inventory_df['Match_Key'] = inventory_df['Name'].str.lower().str.strip() + " " + inventory_df['Artist'].str.lower().str.strip()
    
    missing = target_df[~target_df['Match_Key'].isin(inventory_df['Match_Key'])]
    found = target_df[target_df['Match_Key'].isin(inventory_df['Match_Key'])]
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Tracks Requested", len(target_df))
    m2.metric("Found in Cloud", len(found))
    m3.metric("Gaps (Missing)", len(missing))
    
    t1, t2 = st.tabs(["❌ Missing (Acquisition List)", "✅ Found (Ready to Play)"])
    with t1:
        st.dataframe(missing[['Name', 'Artist']], use_container_width=True, hide_index=True)
    with t2:
        # Show Heritage Data for OGs 
        matches = inventory_df[inventory_df['Match_Key'].isin(found['Match_Key'])]
        st.dataframe(matches[['Name', 'Artist', 'Original_Name', 'Original_Artist', 'Full Path']], use_container_width=True, hide_index=True)
