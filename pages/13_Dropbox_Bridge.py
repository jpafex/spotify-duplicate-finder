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

st.title("📦 Dropbox Bridge (Source-Aware Indexer)")

# 2. Precision Parser
def parse_music_filename(filename):
    clean_name = os.path.splitext(filename)[0]
    # Remove noise
    noise = [r'\(.*?\)', r'\[.*?\]', r'feat\..*', r'ft\..*', r'\d{3}k', r'kbps', r'explicit', r'official']
    for p in noise:
        clean_name = re.sub(p, '', clean_name, flags=re.IGNORECASE)
    
    clean_name = clean_name.strip(' .-_')
    # K-Paz Protection: requires spaces around the dash
    pattern = r"^(?:\d+\s*[.\-_]?\s*)?(.+?)\s+[\-_–—]\s+(.+)$"
    match = re.match(pattern, clean_name)
    
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return "Unknown Artist", clean_name.strip()

# 3. Logic & Connection
if st.button("🔄 Clear Cache & Force Fresh Map"):
    if 'cloud_inventory' in st.session_state:
        del st.session_state['cloud_inventory']
    st.rerun()

try:
    dbx_config = st.secrets["dropbox"]
    dbx = dropbox.Dropbox(
        app_key=dbx_config["app_key"],
        app_secret=dbx_config["app_secret"],
        oauth2_refresh_token=dbx_config["refresh_token"]
    )
except Exception:
    st.error("Missing Dropbox Credentials. Check your secrets.toml.")
    st.stop()

path_to_scan = st.text_input("Folder Path (Leave blank for Root):", value="")

if st.button("🚀 Start Deep Scan & Map"):
    try:
        files_found = []
        formatted_path = "" if path_to_scan.strip() in ["", "/"] else path_to_scan.strip()
        if formatted_path and not formatted_path.startswith("/"):
            formatted_path = "/" + formatted_path

        with st.spinner(f"Indexing {formatted_path if formatted_path else 'Everything'}..."):
            res = dbx.files_list_folder(formatted_path, recursive=True)
            
            def process_entries(entries):
                for entry in entries:
                    if isinstance(entry, dropbox.files.FileMetadata):
                        if entry.name.lower().endswith(('.mp3', '.m4a', '.wav', '.flac')):
                            artist, title = parse_music_filename(entry.name)
                            # Folder Name -> Album field for Triple Match
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
                df = pd.DataFrame(files_found)
                st.session_state['cloud_inventory'] = df
                st.success(f"Index Built: {len(df)} tracks.")

    except Exception as e:
        st.error(f"Scan failed: {e}")

if 'cloud_inventory' in st.session_state:
    df = st.session_state['cloud_inventory']
    st.write("---")
    st.subheader("🔍 Cloud Audit")
    search_q = st.text_input("Search (Try 'K-Paz' or 'Feliz'):")
    
    if search_q:
        filtered_df = df[df.apply(lambda r: search_q.lower() in f"{r['Name']} {r['Artist']}".lower(), axis=1)]
    else:
        filtered_df = df.head(100)

    st.dataframe(filtered_df[['Name', 'Artist', 'Album', 'Source', 'Full Path']], use_container_width=True, hide_index=True)
    
    # BOM-Proof Export
    st.write("---")
    st.subheader("📥 Export for Gap Mirror")
    master_csv = df[['Name', 'Artist', 'Album', 'Source', 'Full Path']].to_csv(index=False).encode('utf-8')
    st.download_button(
        label=f"📥 Download CSV for Auditor ({len(df)} Tracks)",
        data=master_csv,
        file_name=f"Dropbox_Audit_Inventory_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )
