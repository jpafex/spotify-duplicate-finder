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

st.title("📦 Dropbox Bridge")
st.info("Scan your Cloud Library to generate a Virtual Inventory for the Gap Mirror.")

# --- DROPBOX CONFIG ---
# Pro-Tip: Management should store these in Streamlit Secrets for security
DBX_TOKEN = st.sidebar.text_input("Dropbox Access Token", type="password")

# RESET
if st.button("🔄 Clear Cloud Cache"):
    st.rerun()

st.write("---")

# --- SCANNER LOGIC ---
path_to_scan = st.text_input("Dropbox Folder Path to Scan:", value="/Music")

if st.button("🚀 Start Cloud Scan"):
    if not DBX_TOKEN:
        st.error("Please provide a Dropbox Access Token in the sidebar.")
    else:
        try:
            dbx = dropbox.Dropbox(DBX_TOKEN)
            files_found = []
            
            with st.spinner(f"Crawling {path_to_scan}... This may take a moment for large libraries."):
                # Recursive scan of the Dropbox folder
                res = dbx.files_list_folder(path_to_scan, recursive=True)
                
                def process_entries(entries):
                    for entry in entries:
                        if isinstance(entry, dropbox.files.FileMetadata):
                            if entry.name.lower().endswith(('.mp3', '.m4a', '.wav')):
                                # KAIZEN: Extracting Artist/Title from filename if tags aren't cached
                                # Assumes standard "Artist - Title.mp3" format
                                filename = os.path.splitext(entry.name)[0]
                                if " - " in filename:
                                    parts = filename.split(" - ", 1)
                                    artist, title = parts[0], parts[1]
                                else:
                                    artist, title = "Unknown", filename
                                
                                files_found.append({
                                    "Name": title,
                                    "Artist": artist,
                                    "Album": "Cloud Library",
                                    "Path": entry.path_display,
                                    "Size_MB": round(entry.size / (1024 * 1024), 2)
                                })

                process_entries(res.entries)
                
                # Handle pagination for 'enormous' libraries
                while res.has_more:
                    res = dbx.files_list_folder_continue(res.cursor)
                    process_entries(res.entries)

                if files_found:
                    df_cloud = pd.DataFrame(files_found)
                    st.success(f"Cloud Bridge Active: {len(df_cloud)} tracks indexed from Dropbox.")
                    
                    # Dashboard
                    st.metric("Total Library Size", f"{len(df_cloud)} Tracks")
                    
                    st.dataframe(df_cloud, use_container_width=True, hide_index=True)
                    
                    # DOWNLOAD FOR GAP MIRROR
                    # This file is formatted exactly like the MP3Tag export
                    st.subheader("📥 Export for Suite Audit")
                    st.caption("Upload this file into 'Local Files' on the Gap Mirror or Collection Reviewer.")
                    
                    csv_data = df_cloud[['Name', 'Artist', 'Album']].to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 Download Virtual Library CSV",
                        data=csv_data,
                        file_name=f"Dropbox_Inventory_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    st.warning("No music files found in that directory.")
                    
        except Exception as e:
            st.error(f"Dropbox connection failed: {e}")
