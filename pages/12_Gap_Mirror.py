import streamlit as st
import pandas as pd
import gspread
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from google.oauth2.service_account import Credentials
from afexcloud.layout import bootstrap_page

# 1. Page Config
st.set_page_config(page_title="Gap Mirror | AfexCloud", page_icon="🪞", layout="wide")
bootstrap_page()

st.title("🪞 Afex Gap Mirror (Self-Healing Edition)")
st.caption("Syncing Evans/Greeley HQ with the Cloud")

# 2. Handshake Repairs
def get_gspread_client():
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        # Extract and clean the key
        info = dict(st.secrets["google_gsheets"])
        # Replace literal \n and clean hidden whitespace at the end
        info["private_key"] = info["private_key"].replace("\\n", "\n").strip()
        creds = Credentials.from_service_account_info(info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Google GSheets Error: {e}")
        return None

def get_spotify_client():
    try:
        # Pull from the dedicated [spotify] block
        config = st.secrets["spotify"]
        client_id = config["client_id"].strip()
        client_secret = config["client_secret"].strip()
        
        # Explicit credentials manager
        auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
        return spotipy.Spotify(auth_manager=auth_manager)
    except Exception as e:
        st.error(f"❌ Spotify 401/Auth Error: {e}")
        return None

# 3. Step 1: Harvest Client Requests
st.subheader("📡 Step 1: Connect Client Playlist")
target_mode = st.radio("Source:", ["Direct Spotify Link", "Client Google Sheet", "CSV"])

target_df = None
if target_mode == "Direct Spotify Link":
    p_url = st.text_input("Spotify URL:")
    if p_url and st.button("🚀 Harvest"):
        sp = get_spotify_client()
        if sp:
            try:
                p_id = p_url.split('/')[-1].split('?')[0]
                res = sp.playlist_items(p_id)
                target_df = pd.DataFrame([{"Name": i['track']['name'], "Artist": i['track']['artists'][0]['name']} for i in res['items'] if i['track']])
                st.success(f"Found {len(target_df)} tracks.")
            except Exception as e:
                st.error(f"Spotify Harvest Error: {e}")

elif target_mode == "Client Google Sheet":
    c_url = st.text_input("Client Sheet URL:")
    if c_url:
        gc = get_gspread_client()
        if gc:
            try:
                sh = gc.open_by_url(c_url.split('/edit')[0]).get_worksheet(0)
                target_df = pd.DataFrame(sh.get_all_records())
                st.success("Connected to Client Sheet.")
            except Exception as e:
                st.error(f"GSheet Error: {e}")

# 4. Step 2: Sync Master Inventory
st.write("---")
st.subheader("📦 Step 2: Sync Master Inventory")
master_url = st.text_input("Master URL:", value="https://docs.google.com/spreadsheets/d/1lHZm2gniKaODA60T50oHnMWl-ajZGJ1jkNUtm7TbHbs")

inventory_df = None
if master_url:
    gc = get_gspread_client()
    if gc:
        try:
            sh = gc.open_by_url(master_url.split('/edit')[0]).get_worksheet(0)
            inventory_df = pd.DataFrame(sh.get_all_records())
            st.info(f"Inventory Live: {len(inventory_df)} tracks synced.")
        except Exception as e:
            st.error(f"Inventory Connection Failed: {e}")

# 5. Step 3: Audit Result
if target_df is not None and inventory_df is not None:
    st.write("---")
    # Matching Engine
    target_df['Match_Key'] = target_df['Name'].astype(str).str.lower().str.strip() + " " + target_df['Artist'].astype(str).str.lower().str.strip()
    inventory_df['Match_Key'] = inventory_df['Name'].astype(str).str.lower().str.strip() + " " + inventory_df['Artist'].astype(str).str.lower().str.strip()
    
    missing = target_df[~target_df['Match_Key'].isin(inventory_df['Match_Key'])]
    found = target_df[target_df['Match_Key'].isin(inventory_df['Match_Key'])]
    
    st.subheader(f"🔍 Gaps Found: {len(missing)}")
    t1, t2 = st.tabs(["❌ Gaps", "✅ Found"])
    with t1:
        st.dataframe(missing[['Name', 'Artist']], use_container_width=True, hide_index=True)
    with t2:
        matches = inventory_df[inventory_df['Match_Key'].isin(found['Match_Key'])]
        st.dataframe(matches[['Name', 'Artist', 'Original_Name', 'Original_Artist', 'Full Path']], use_container_width=True, hide_index=True)
