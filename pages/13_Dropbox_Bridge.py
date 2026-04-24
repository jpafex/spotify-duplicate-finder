import streamlit as st
import pandas as pd
import dropbox
import os
import re
from datetime import datetime
from afexcloud.layout import bootstrap_page

# 1. Page Config
st.set_page_config(page_title="Dropbox Bridge | AfexCloud", page_icon="📦", layout="wide")
bootstrap_page()

st.title("📦 Dropbox Bridge (Heavy-Duty Indexer)")

# 2. THE REFINED PARSER
def parse_music_filename(filename):
    clean_name = os.path.splitext(filename)[0]
    # Remove metadata noise commonly found in cloud music
    noise = [r'\(.*?\)', r'\[.*?\]', r'feat\..*', r'ft\..*', r'\d{3}k', r'kbps', r'explicit', r'official']
    for p in noise:
        clean_name = re.sub(p, '', clean_name, flags=re.IGNORECASE)
    
    clean_name = clean_name.strip(' .-_')
    # Standard delimiters including long dashes
    pattern = r"^(?:\d+\s*[.\-_]?\s*)?(.+?)\s*[\-_–—]\s*(.+)$"
    match = re.match(pattern, clean_name)
    
    if match:
        return match.group(1).strip().title(), match.group(2).strip().title()
    return "Unknown Artist", clean_name.strip().title()

# 3. Connection & Logic
if st.button("🔄 Clear and Refresh Cloud Cache"):
    st.rerun()

try:
    dbx_config = st.secrets["dropbox"]
    dbx = dropbox.Dropbox(
        app_key=dbx_config["app_key"],
        app_secret=dbx_config["app_secret"],
        oauth2_refresh_token=dbx_config["refresh_token"]
    )
except Exception:
    st.error("Missing Dropbox Credentials in secrets.toml.")
    st.stop()

path_to_scan = st.text_input("Folder Path (Leave blank for Root):", value="")

if st.button("🚀 Start Deep Scan"):
    try:
        files_found = []
        formatted_path = "" if path_to_scan.strip() in ["", "/"] else path_to_scan.strip()
        if formatted_path and not formatted_path.startswith("/"):
            formatted_path = "/" + formatted_path

        with st.spinner(f"Crawling {len(formatted_path) if formatted_path else 'Entire Library'}..."):
            res = dbx.files_list_folder(formatted_path, recursive=True)
            
            def process_entries(entries):
                for entry in entries:
                    if isinstance(entry, dropbox.files.FileMetadata):
                        if entry.name.lower().endswith(('.mp3', '.m4a', '.wav')):
                            artist, title = parse_music_filename(entry.name)
                            files_found.append({
                                "Name": title,
                                "Artist": artist,
                                "Album": "Cloud Library",
                                "Raw Filename": entry.name
                            })

            process_entries(res.entries)
            while res.has_more:
                res = dbx.files_list_folder_continue(res.cursor)
                process_entries(res.entries)

            if files_found:
                df = pd.DataFrame(files_found)
                st.session_state['cloud_inventory'] = df
                st.success(f"Index Built: {len(df)} tracks categorized.")

    except Exception as e:
        st.error(f"Scan failed: {e}")

# 4. CLOUD INVENTORY SEARCH & AUDIT
if 'cloud_inventory' in st.session_state:
    df = st.session_state['cloud_inventory']
    
    st.write("---")
    st.subheader("🔍 Cloud Library Audit")
    search_q = st.text_input("Search 45k Library (by Artist or Title):")
    
    if search_q:
        filtered_df = df[df.apply(lambda r: search_q.lower() in str(r).lower(), axis=1)]
    else:
        filtered_df = df.head(100) # Show first 100 for speed

    st.dataframe(filtered_df, use_container_width=True, hide_index=True)
    
    # Gap Mirror Bridge
    st.download_button(
        label=f"📥 Download Audit CSV for Gap Mirror ({len(df)} Tracks)",
        data=df[['Name', 'Artist', 'Album']].to_csv(index=False).encode('utf-8-sig'),
        file_name=f"Dropbox_Master_Inventory_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
