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

st.title("📦 Dropbox Bridge (BOM-Proof Edition)")

# 2. THE REFINED PARSER
def parse_music_filename(filename):
    """
    HEAVY-DUTY PARSER: 
    1. Protects hyphenated names like K-Paz by requiring spaces.
    2. Fallback logic for filenames with NO spaces (e.g., Artist-Title).
    """
    clean_name = os.path.splitext(filename)[0]
    # Remove metadata noise
    noise = [r'\(.*?\)', r'\[.*?\]', r'feat\..*', r'ft\..*', r'\d{3}k', r'kbps', r'explicit', r'official']
    for p in noise:
        clean_name = re.sub(p, '', clean_name, flags=re.IGNORECASE)
    
    clean_name = clean_name.strip(' .-_')
    
    # Try the 'Space-Dash-Space' first (Precision Mode for K-Paz)
    precision_pattern = r"^(?:\d+\s*[.\-_]?\s*)?(.+?)\s+[\-_–—]\s+(.+)$"
    match = re.match(precision_pattern, clean_name)
    
    if match:
        return match.group(1).strip(), match.group(2).strip()
    
    # Fallback: Standard dash split (Standard Mode)
    standard_pattern = r"^(?:\d+\s*[.\-_]?\s*)?(.+?)[\-_–—](.+)$"
    match = re.match(standard_pattern, clean_name)
    if match:
        return match.group(1).strip(), match.group(2).strip()
        
    return "Unknown Artist", clean_name.strip()

# 3. Connection & Logic
# KAIZEN: Ensuring session state is handled correctly to avoid NameErrors
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

        with st.spinner(f"Mapping {formatted_path if formatted_path else 'Entire Library'}..."):
            res = dbx.files_list_folder(formatted_path, recursive=True)
            
            def process_entries(entries):
                for entry in entries:
                    if isinstance(entry, dropbox.files.FileMetadata):
                        if entry.name.lower().endswith(('.mp3', '.m4a', '.wav')):
                            artist, title = parse_music_filename(entry.name)
                            # Extract folder name
                            raw_folder = os.path.basename(os.path.dirname(entry.path_display))
                            folder_name = raw_folder if raw_folder else "Root"
                            
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
                st.success(f"Mapping Complete: {len(df)} tracks correctly parsed.")

    except Exception as e:
        st.error(f"Scan failed: {e}")

# 4. Search & Export
if 'cloud_inventory' in st.session_state:
    df = st.session_state['cloud_inventory']
    
    st.write("---")
    st.subheader("🔍 Precision Audit")
    search_q = st.text_input("Verify Artist/Title Parsing (Try 'K-Paz'):")
    
    if search_q:
        filtered_df = df[df.apply(lambda r: search_q.lower() in f"{r['Name']} {r['Artist']}".lower(), axis=1)]
    else:
        filtered_df = df.head(100)

    st.dataframe(filtered_df[['Name', 'Artist', 'Folder', 'Full Path']], use_container_width=True, hide_index=True)
    
    # KAIZEN: Use standard 'utf-8' to prevent BOM errors in the Gap Mirror
    st.write("---")
    st.subheader("📥 Export Master Audit")
    master_csv = df[['Name', 'Artist', 'Album', 'Folder', 'Full Path']].to_csv(index=False).encode('utf-8')
    st.download_button(
        label=f"📥 Download Master Cloud Inventory ({len(df)} Tracks)",
        data=master_csv,
        file_name=f"Dropbox_Mapped_Inventory_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )
