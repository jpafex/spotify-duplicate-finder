import streamlit as st
import pandas as pd
import dropbox
import os
import re
import gspread
import pytz
from google.oauth2.service_account import Credentials
from datetime import datetime
from afexcloud.layout import bootstrap_page

# 1. Page Config
st.set_page_config(page_title="Dropbox Bridge | AfexCloud", page_icon="📦", layout="wide")
bootstrap_page()

st.title("📦 Dropbox Bridge (Dynamic Edition)")
st.caption("Windows | Mac | ChromeOS | iOS | 59,132 Track Support")

# 2. Precision Parser
def parse_music_filename(filename):
    clean_name = os.path.splitext(filename)[0]
    noise = [r'\(.*?\)', r'\[.*?\]', r'feat\..*', r'ft\..*', r'\d{3}k', r'kbps', r'explicit']
    for p in noise:
        clean_name = re.sub(p, '', clean_name, flags=re.IGNORECASE)
    clean_name = clean_name.strip(' .-_')
    
    pattern = r"^(?:\d+\s*[.\-_]?\s*)?(.+?)\s+[\-_–—]\s+(.+)$"
    match = re.match(pattern, clean_name)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return "Unknown Artist", clean_name.strip()

# 3. Connection
try:
    dbx_config = st.secrets["dropbox"]
    dbx = dropbox.Dropbox(app_key=dbx_config["app_key"], app_secret=dbx_config["app_secret"], oauth2_refresh_token=dbx_config["refresh_token"])
except Exception:
    st.error("Check secrets.toml for Dropbox credentials.")
    st.stop()

# 4. Scanning Logic
path_to_scan = st.text_input("Folder Path to Map (e.g. /Chilenas):", value="")

if st.button("🚀 Start Precision Cloud Scan"):
    try:
        files_found = []
        formatted_path = "" if path_to_scan.strip() in ["", "/"] else path_to_scan.strip()
        if formatted_path and not formatted_path.startswith("/"): formatted_path = "/" + formatted_path

        # --- DYNAMIC MESSAGE LOGIC ---
        # If no scan has run yet, it defaults to your new 59,132 milestone
        last_count = st.session_state.get('last_track_count', "59,132")
        
        with st.spinner(f"Indexing {last_count} tracks..."):
            res = dbx.files_list_folder(formatted_path, recursive=True)
            def process_entries(entries):
                for entry in entries:
                    if isinstance(entry, dropbox.files.FileMetadata) and entry.name.lower().endswith(('.mp3', '.m4a', '.wav')):
                        art, tit = parse_music_filename(entry.name)
                        fld = os.path.basename(os.path.dirname(entry.path_display)) or "Root"
                        files_found.append({
                            "Name": tit, "Artist": art, "Album": fld,
                            "Source": "Cloud Library", "Original_Name": tit, 
                            "Original_Artist": art, "Full Path": entry.path_display
                        })
            process_entries(res.entries)
            while res.has_more:
                res = dbx.files_list_folder_continue(res.cursor)
                process_entries(res.entries)

            if files_found:
                st.session_state['cloud_inventory'] = pd.DataFrame(files_found)
                st.session_state['last_track_count'] = f"{len(files_found):,}"
                st.success(f"Index Built: {len(files_found)} tracks identified.")
    except Exception as e:
        st.error(f"Scan failed: {e}")

# 5. THE GOOGLE SHEETS SYNC ENGINE
if 'cloud_inventory' in st.session_state:
    df = st.session_state['cloud_inventory']
    st.write("---")
    st.subheader("📥 Export & Sync Center")
    
    mode = st.radio("Choose Performance Mode:", ["Sync to Google Sheets (Live)", "Download Local CSV"])

    if mode == "Sync to Google Sheets (Live)":
        st.info("💡 Chromebook/iPad Compatible: This pushes the data directly to your live master sheet.")
        
        # Hardcoded Default URL Logic
        use_default = st.checkbox("Use Afex Master Inventory Sheet (Default)", value=True)
        default_url = "https://docs.google.com/spreadsheets/d/1lHZm2gniKaODA60T50oHnMWl-ajZGJ1jkNUtm7TbHbs"
        sheet_url = default_url if use_default else st.text_input("Custom Google Sheet URL:")
        
        if st.button("🔄 Execute Live Sync"):
            try:
                # --- THE UNIVERSAL SCRUBBER: KILLS PEM ERROR 1627 ---
                info = dict(st.secrets["google_gsheets"])
                # 1. Handle literal \n and real newlines
                key = info["private_key"].replace("\\n", "\n").strip()
                # 2. Reconstruct clean header/footer with exact single newlines
                key = re.sub(r'-----BEGIN PRIVATE KEY-----', '-----BEGIN PRIVATE KEY-----\n', key)
                key = re.sub(r'-----END PRIVATE KEY-----', '\n-----END PRIVATE KEY-----', key)
                # 3. Aggressively remove any hidden spaces/carriage returns from the middle
                lines = [line.strip() for line in key.split('\n') if line.strip()]
                info["private_key"] = "\n".join(lines)
                
                scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
                creds = Credentials.from_service_account_info(info, scopes=scope)
                client = gspread.authorize(creds)
                
                clean_url = sheet_url.split('/edit')[0]
                sheet = client.open_by_url(clean_url).get_worksheet(0)
                sheet.clear()
                sheet.update([df.columns.values.tolist()] + df.values.tolist())
                
                # --- MOUNTAIN TIME TIMESTAMP (12-HOUR FORMAT) ---
                mt_zone = pytz.timezone('US/Mountain')
                sync_time = datetime.now(mt_zone).strftime("%m-%d-%Y %I:%M:%S %p")
                sheet.update_acell('I1', f"Last Sync (MT): {sync_time}")
                
                st.success(f"Success! {len(df)} tracks are live. Last Sync: {sync_time}")
                st.balloons()
            except Exception as e:
                st.error(f"Sync failed: {e}")
    else:
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Master CSV", csv_data, "Afex_Cloud_Inventory.csv", "text/csv")
