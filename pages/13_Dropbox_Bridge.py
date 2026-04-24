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

st.title("📦 Dropbox Bridge (Smart Cloud Indexer)")

# 2. Refined Parsing Logic (The Smart Parser)
def parse_music_filename(filename):
    """
    KAIZEN: Uses Regex to intelligently separate Artist and Title.
    Handles track numbers, underscores, and multiple hyphens.
    """
    # Remove extension
    clean_name = os.path.splitext(filename)[0]
    
    # Pattern: Optional track number, followed by Artist and Title separated by ' - ' or ' _ '
    # e.g., "01 Grupo Mister - Juego de Amor" -> Artist: Grupo Mister, Title: Juego de Amor
    pattern = r"^(?:\d+\s*[.\-_]?\s*)?(.+?)\s*[\-_]\s*(.+)$"
    match = re.match(pattern, clean_name)
    
    if match:
        artist = match.group(1).strip()
        title = match.group(2).strip()
    else:
        # Fallback if no delimiter is found
        artist = "Unknown Artist"
        title = clean_name
        
    return artist, title

# 3. Tool Logic
if st.button("🔄 Refresh Cloud Inventory"):
    st.rerun()

st.info("🧬 **Smart Indexing Active**: Crawling Dropbox and parsing filenames for the Gap Mirror.")

# SECURE CONNECTION: Using the Refresh Token from Secrets
try:
    dbx_config = st.secrets["dropbox"]
    dbx = dropbox.Dropbox(
        app_key=dbx_config["app_key"],
        app_secret=dbx_config["app_secret"],
        oauth2_refresh_token=dbx_config["refresh_token"]
    )
except Exception:
    st.error("Missing Dropbox Credentials. Please check your secrets.toml file.")
    st.stop()

path_to_scan = st.text_input("Dropbox Folder Path to Index:", value="/Music")

if st.button("🚀 Start Cloud Scan"):
    try:
        files_found = []
        with st.spinner(f"Indexing {path_to_scan}..."):
            # Recursive scan
            res = dbx.files_list_folder(path_to_scan, recursive=True)
            
            def process_entries(entries):
                for entry in entries:
                    if isinstance(entry, dropbox.files.FileMetadata):
                        if entry.name.lower().endswith(('.mp3', '.m4a', '.wav')):
                            artist, title = parse_music_filename(entry.name)
                            files_found.append({
                                "Name": title,
                                "Artist": artist,
                                "Album": "Cloud Library",
                                "Filename": entry.name,
                                "Path": entry.path_display
                            })

            process_entries(res.entries)
            
            # Handle Large Library Pagination
            while res.has_more:
                res = dbx.files_list_folder_continue(res.cursor)
                process_entries(res.entries)

            if files_found:
                df_cloud = pd.DataFrame(files_found)
                st.success(f"Index Complete: {len(df_cloud)} tracks found in the cloud.")
                
                # Metrics Dashboard
                st.metric("Cloud Library Size", f"{len(df_cloud)} Tracks")
                
                # Preview Table
                st.dataframe(df_cloud[['Name', 'Artist', 'Filename']], use_container_width=True, hide_index=True)
                
                # --- EXPORT FOR GAP MIRROR ---
                st.write("---")
                st.subheader("📥 Export for Audit")
                st.caption("Download this CSV and upload it as 'Local Files' in the Gap Mirror tool.")
                
                csv_data = df_cloud[['Name', 'Artist', 'Album']].to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 Download Virtual Library CSV",
                    data=csv_data,
                    file_name=f"Cloud_Inventory_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.warning("No music files found. Ensure the path is correct (e.g., /MyMusic).")
                
    except Exception as e:
        st.error(f"Cloud scan failed: {e}")
