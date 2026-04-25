import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime
from afexcloud.layout import bootstrap_page

# 1. Page Config
st.set_page_config(page_title="Virtual Architect | AfexCloud", page_icon="📑", layout="wide")
bootstrap_page()

st.title("📑 Afex Virtual Architect")
st.caption("Metadata Standardization | Disk-Space Optimized | Phase-Based Migration")

# 2. Data Check
if 'cloud_inventory' not in st.session_state:
    st.error("🚨 **Inventory Missing**: Run a scan in 'Dropbox Bridge' (Page 13) first.")
    st.stop()

df = st.session_state['cloud_inventory'].copy()

# 3. THE VIRTUAL MAPPING ENGINE
def get_clean_metadata(row):
    # Remove illegal characters for Windows/Google Drive
    artist = re.sub(r'[\\/*?:"<>|]', "", str(row['Artist']))
    name = re.sub(r'[\\/*?:"<>|]', "", str(row['Name']))
    ext = os.path.splitext(row['Full Path'])[1]
    return f"{artist} - {name}{ext}"

df['Clean_Filename'] = df.apply(get_clean_metadata, axis=1)

# 4. Management Review Section
st.write("---")
st.subheader("📊 Step 1: Master Metadata Audit")
st.info(f"Generating a virtual map for **{len(df)}** tracks. This uses ZERO disk space.")

# Display the "Before vs After" for Management
audit_df = df[['Artist', 'Name', 'Album', 'Clean_Filename', 'Full Path']]
st.dataframe(audit_df.head(100), use_container_width=True, hide_index=True)

# THE MASTER CSV DOWNLOAD
st.write("---")
master_clean_csv = df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Download Master Cleaned CSV (For Management Review)",
    data=master_clean_csv,
    file_name=f"Afex_Master_Clean_Index_{datetime.now().strftime('%Y%m%d')}.csv",
    mime="text/csv",
    use_container_width=True
)

# 5. THE PIECE-MEAL MIGRATOR (Event Focused)
st.write("---")
st.subheader("⚡ Step 2: Piece-meal Migration (Event Prep)")
st.caption("Clean and move only the songs you need for your next gig.")

event_search = st.text_input("Find songs for this event (e.g., 'Chilenas' or 'Grupo Origen'):")
if event_search:
    event_df = df[df.apply(lambda r: event_search.lower() in f"{r['Name']} {r['Artist']} {r['Album']}".lower(), axis=1)].copy()
    st.write(f"Found **{len(event_df)}** tracks for this migration batch.")
    st.dataframe(event_df[['Clean_Filename', 'Album']], use_container_width=True, hide_index=True)
    
    local_root = st.text_input("Enter Local Dropbox Root (e.g., D:/Dropbox):", key="local_migrate")
    
    if local_root and st.button("🚀 Generate Migration Script for this Batch"):
        local_root = local_root.replace("\\", "/").rstrip("/") + "/"
        commands = [f'New-Item -ItemType Directory -Force -Path "{local_root}Afex_Clean_Library"']
        
        for idx, row in event_df.iterrows():
            src = (local_root + row['Full Path'].lstrip("/")).replace("/", "\\")
            dest_folder = f"{local_root}Afex_Clean_Library/{re.sub(r'[\\/*?:\'\"<>|]', '', str(row['Album']))}".replace("/", "\\")
            commands.append(f'New-Item -ItemType Directory -Force -Path "{dest_folder}"')
            dest_file = f"{dest_folder}\\{row['Clean_Filename']}"
            commands.append(f'Copy-Item -Path "{src}" -Destination "{dest_file}" -Force -ErrorAction SilentlyContinue')
        
        st.download_button(
            label=f"📥 Download Batch Migration Script ({len(event_df)} files)",
            data="\n".join(commands),
            file_name=f"Event_Migration_{event_search.replace(' ', '_')}.ps1",
            mime="text/plain"
        )
