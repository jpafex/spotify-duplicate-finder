import streamlit as st
import pandas as pd
import gspread
import spotipy
import traceback
from spotipy.oauth2 import SpotifyClientCredentials
from google.oauth2.service_account import Credentials
from afexcloud.layout import bootstrap_page

# 1. Page Config & Branding
st.set_page_config(page_title="Gap Mirror | AfexCloud", page_icon="🪞", layout="wide")
bootstrap_page()

st.title("🪞 Afex Gap Mirror (Cloud Edition)")
st.caption("Zero-File Workflow | Spotify & GSheets Integrated | Evans/Greeley HQ")

# 2. Connection Handshakes (Bulletproof Edition)
def get_gspread_client():
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        # Pulls from the [google_gsheets] section we fixed
        info = dict(st.secrets["google_gsheets"])
        # AUTOMATIC KEY REPAIR: Fixes the 'Unable to load PEM' error
        info["private_key"] = info["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Google GSheets Connection Failed: {e}")
        return None

def get_spotify_client():
    try:
        # Looking in the NEW [spotify] section for 2026 compliance
        config = st.secrets.get("spotify")
        if not config:
            st.error("🚨 Spotify Secrets missing! Ensure [spotify] section exists.")
            return None
        
        return spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=config["client_id"],
            client_secret=config["client_secret"]
        ))
    except Exception as e:
        if "401" in str(e):
            st.error("🚨 Spotify Auth Failed (401): Check Client ID/Secret or Playlist Privacy.")
        else:
            st.error(f"❌ Spotify Connection Failed: {e}")
        return None

# 3. Step 1: Identify Client Requests (The "Target")
st.subheader("📡 Step 1: Connect Client Playlist")
target_mode = st.radio("Fetch Request List From:", ["Direct Spotify Link", "Client Google Sheet", "Manual CSV Upload"])

target_df = None

if target_mode == "Direct Spotify Link":
    p_url = st.text_input("Paste Spotify Playlist URL:", placeholder="https://open.spotify.com/playlist/...")
    st.info("💡 Note: Ensure the playlist is set to **'Public'**.")
    if p_url and st.button("🚀 Harvest Tracks"):
        with st.spinner("Harvesting metadata..."):
            sp = get_spotify_client()
            if sp:
                try:
                    p_id = p_url.split('/')[-1].split('?')[0]
                    results = sp.playlist_items(p_id)
                    data = [{"Name": i['track']['name'], "Artist": i['track']['artists'][0]['name']} for i in results['items'] if i['track']]
                    target_df = pd.DataFrame(data)
                    st.success(f"Harvested {len(target_df)} tracks.")
                except Exception as e:
                    st.error(f"Harvest Error: {e}")

elif target_mode == "Client Google Sheet":
    c_url = st.text_input("Paste Client Google Sheet URL:")
    if c_url:
        try:
            client = get_gspread_client()
            if client:
                sheet = client.open_by_url(c_url.split('/edit')[0]).get_worksheet(0)
                target_df = pd.DataFrame(sheet.get_all_records())
                st.success(f"Pulled {len(target_df)} tracks from Client Sheet.")
        except Exception as e:
            st.error(f"GSheet Error: {e}")

else:
    c_file = st.file_uploader("Upload Client CSV", type=['csv'])
    if c_file:
        target_df = pd.read_csv(c_file)

# 4. Step 2: Sync Master Inventory (The "Warehouse")
st.write("---")
st.subheader("📦 Step 2: Connect Master Inventory")
# Set to your successful Dropbox Bridge sheet
master_url = st.text_input("Master Inventory URL:", value="https://docs.google.com/spreadsheets/d/1lHZm2gniKaODA60T50oHnMWl-ajZGJ1jkNUtm7TbHbs")

inventory_df = None
if master_url:
    try:
        client = get_gspread_client()
        if client:
            sheet = client.open_by_url(master_url.split('/edit')[0]).get_worksheet(0)
            inventory_df = pd.DataFrame(sheet.get_all_records())
            st.info(f"Inventory Live: {len(inventory_df)} tracks synced from Cloud.")
    except Exception as e:
        st.error(f"Inventory Connection Failed: {e}")

# 5. Step 3: Execute Audit
if target_df is not None and inventory_df is not None:
    st.write("---")
    st.subheader("🔍 Step 3: Audit Results")
    
    # Matching Engine (Standardize for 100% Precision)
    target_df['Match_Key'] = target_df['Name'].astype(str).str.lower().str.strip() + " " + target_df['Artist'].astype(str).str.lower().str.strip()
    inventory_df['Match_Key'] = inventory_df['Name'].astype(str).str.lower().str.strip() + " " + inventory_df['Artist'].astype(str).str.lower().str.strip()
    
    missing = target_df[~target_df['Match_Key'].isin(inventory_df['Match_Key'])]
    found = target_df[target_df['Match_Key'].isin(inventory_df['Match_Key'])]
    
    # Performance Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Tracks Requested", len(target_df))
    m2.metric("Found in Cloud", len(found))
    m3.metric("Gaps (Missing)", len(missing))
    
    # Detailed Tabs
    t1, t2 = st.tabs(["❌ Gaps (Acquisition List)", "✅ Found (Ready to Play)"])
    
    with t1:
        st.dataframe(missing[['Name', 'Artist']], use_container_width=True, hide_index=True)
        if not missing.empty:
            csv = missing.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Gap List", csv, "needed_tracks.csv", "text/csv")
    
    with t2:
        # Show Heritage Data for OGs (Original Artist/Name from the Cloud Scan)
        matches = inventory_df[inventory_df['Match_Key'].isin(found['Match_Key'])]
        st.dataframe(matches[['Name', 'Artist', 'Original_Name', 'Original_Artist', 'Full Path']], 
                     use_container_width=True, hide_index=True)
