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

st.title("📦 Dropbox Bridge (Library Mapper)")

# 2. Heavy-Duty Parser
def parse_music_filename(filename):
    clean_name = os.path.splitext(filename)[0]
    noise = [r'\(.*?\)', r'\[.*?\]', r'feat\..*', r'ft\..*', r'\d{3}k', r'kbps', r'explicit', r'official']
    for p in noise:
        clean_name = re.sub(p, '', clean_name, flags=re.IGNORECASE)
    
    clean_name = clean_name.strip(' .-_')
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

if st.button("🚀 Start Deep Scan & Map"):
    try:
        files_found = []
        formatted_path = "" if path_to_scan.strip() in ["", "/"] else path_to_scan.strip()
        if formatted_path and not formatted_path.startswith("/"):
            formatted_path = "/" + formatted_path

        with st.spinner(f"Mapping {formatted_path if formatted_path else 'Entire Library'}..."):
            res = dbx.files_list_folder(formatted_path, recursive=True)
            
            def process_entries(entries):
                for entry in entries:
                    if isinstance(entry, dropbox.files.FileMetadata):
                        if entry.name.lower().endswith(('.mp3', '.m4a', '.wav')):
                            artist, title = parse_music_filename(entry.name)
                            
                            # KAIZEN: Extract the Immediate Parent Folder Name
                            # Path looks like: /Music/Latin/Cumbia/Song.mp3 -> Folder: Cumbia
                            folder_name = os.path.basename(os.path.dirname(entry.path_display))
                            
                            files_found.append({
                                "Name": title,
                                "Artist": artist,
                                "Album": "Cloud Library",
                                "Folder": folder_name,
                                "Full Path": entry.path_display
                            })

            process_entries(res.entries)
            while res.has_more:
                res = dbx.files_list_folder_continue(res.cursor)
                process_entries(res.entries)

            if files_found:
                df = pd.DataFrame(files_found)
                st.session_state['cloud_inventory'] = df
                st.success(f"Mapping Complete: {len(df)} tracks categorized across your folders.")

    except Exception as e:
        st.error(f"Scan failed: {e}")

# 4. CLOUD INVENTORY SEARCH & AUDIT
if 'cloud_inventory' in st.session_state:
    df = st.session_state['cloud_inventory']
    
    # --- KAIZEN: FOLDER NAVIGATOR ---
    st.write("---")
    with st.expander("📂 Folder Navigator", expanded=False):
        # Extract unique folder names
        unique_folders = sorted(df['Folder'].unique().tolist())
        st.write(f"Your library is organized into **{len(unique_folders)}** unique folders.")
        
        selected_folder = st.selectbox("View contents of a specific folder:", ["All Folders"] + unique_folders)
        
        if selected_folder != "All Folders":
            folder_view = df[df['Folder'] == selected_folder]
            st.write(f"Displaying **{len(folder_view)}** tracks in `{selected_folder}`")
            st.dataframe(folder_view[['Name', 'Artist', 'Full Path']], use_container_width=True, hide_index=True)

    # --- SEARCH & AUDIT ---
    st.write("---")
    st.subheader("🔍 Library Audit Search")
    search_q = st.text_input("Search Artist, Title, or Folder:")
    
    if search_q:
        # Search across all three main columns
        filtered_df = df[df.apply(lambda r: search_q.lower() in f"{r['Name']} {r['Artist']} {r['Folder']}".lower(), axis=1)]
    else:
        filtered_df = df.head(100)

    st.dataframe(filtered_df[['Name', 'Artist', 'Folder', 'Full Path']], use_container_width=True, hide_index=True)
    
    # Gap Mirror Bridge with FOLDER data
    st.write("---")
    st.subheader("📥 Export Master Audit")
    st.caption("This CSV now includes the 'Folder' column to help your team locate files quickly.")
    
    # We include Folder in the download so it shows up in the Gap Mirror
    master_csv = df[['Name', 'Artist', 'Album', 'Folder', 'Full Path']].to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label=f"📥 Download Master Cloud Inventory ({len(df)} Tracks)",
        data=master_csv,
        file_name=f"Dropbox_Mapped_Inventory_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )
