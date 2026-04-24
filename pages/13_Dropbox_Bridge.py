import streamlit as st
import pandas as pd
import dropbox
import os
import re
from datetime import datetime
from afexcloud.layout import bootstrap_page

st.set_page_config(page_title="Dropbox Bridge | AfexCloud", page_icon="📦", layout="wide")
bootstrap_page()

st.title("📦 Dropbox Bridge (100% Precision)")

def parse_music_filename(filename):
    clean_name = os.path.splitext(filename)[0]
    noise = [r'\(.*?\)', r'\[.*?\]', r'feat\..*', r'ft\..*', r'\d{3}k', r'kbps', r'explicit']
    for p in noise:
        clean_name = re.sub(p, '', clean_name, flags=re.IGNORECASE)
    clean_name = clean_name.strip(' .-_')
    
    # K-Paz Protection
    precision_pattern = r"^(?:\d+\s*[.\-_]?\s*)?(.+?)\s+[\-_–—]\s+(.+)$"
    match = re.match(precision_pattern, clean_name)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    
    # Fallback dash split
    standard_pattern = r"^(?:\d+\s*[.\-_]?\s*)?(.+?)[\-_–—](.+)$"
    match = re.match(standard_pattern, clean_name)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return "Unknown Artist", clean_name.strip()

if st.button("🔄 Clear Cache & Force Fresh Map"):
    if 'cloud_inventory' in st.session_state:
        del st.session_state['cloud_inventory']
    st.rerun()

try:
    dbx_config = st.secrets["dropbox"]
    dbx = dropbox.Dropbox(app_key=dbx_config["app_key"], app_secret=dbx_config["app_secret"], oauth2_refresh_token=dbx_config["refresh_token"])
except Exception:
    st.error("Check secrets.toml for Dropbox credentials.")
    st.stop()

path_to_scan = st.text_input("Folder Path:", value="")

if st.button("🚀 Start Deep Scan"):
    try:
        files_found = []
        formatted_path = "" if path_to_scan.strip() in ["", "/"] else path_to_scan.strip()
        if formatted_path and not formatted_path.startswith("/"): formatted_path = "/" + formatted_path

        with st.spinner("Indexing 45k tracks..."):
            res = dbx.files_list_folder(formatted_path, recursive=True)
            def process_entries(entries):
                for entry in entries:
                    if isinstance(entry, dropbox.files.FileMetadata) and entry.name.lower().endswith(('.mp3', '.m4a', '.wav')):
                        artist, title = parse_music_filename(entry.name)
                        # KAIZEN: Promote Folder to Album for Triple Match
                        raw_folder = os.path.basename(os.path.dirname(entry.path_display))
                        folder_name = raw_folder if raw_folder else "Root"
                        files_found.append({
                            "Name": title,
                            "Artist": artist,
                            "Album": folder_name,
                            "Source": "Cloud Library",
                            "Full Path": entry.path_display
                        })
            process_entries(res.entries)
            while res.has_more:
                res = dbx.files_list_folder_continue(res.cursor)
                process_entries(res.entries)

            if files_found:
                st.session_state['cloud_inventory'] = pd.DataFrame(files_found)
                st.success(f"Index Built: {len(files_found)} tracks.")
    except Exception as e:
        st.error(f"Scan failed: {e}")

if 'cloud_inventory' in st.session_state:
    df = st.session_state['cloud_inventory']
    st.dataframe(df.head(100), use_container_width=True, hide_index=True)
    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Master Inventory", data=csv_data, file_name="Dropbox_100_Inventory.csv", mime="text/csv")
