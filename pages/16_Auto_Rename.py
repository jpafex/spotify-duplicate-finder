import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime
from afexcloud.layout import bootstrap_page

# 1. Page Config
st.set_page_config(page_title="Virtual Architect | AfexCloud", page_icon="📑", layout="wide")
bootstrap_page()

st.title("📑 Afex Virtual Architect (Heritage Edition)")
st.caption("Cleaned Metadata | OG Data Preservation | Evans/Greeley HQ")

# 2. Data Check
if 'cloud_inventory' not in st.session_state:
    st.error("🚨 **Inventory Missing**: Run a scan in 'Dropbox Bridge' (Page 13) first.")
    st.stop()

# We work on a copy to keep the original session state clean
df = st.session_state['cloud_inventory'].copy()

# 3. THE CLEANING ENGINE (Blueprints)
def clean_text(text):
    if not isinstance(text, str): return ""
    # Standard Afex Clean: Remove noise, fix casing, remove illegal chars
    text = re.sub(r'[\\/*?:"<>|]', "", text)
    return text.strip()

# Preserve the "OG" data before we modify the main columns
df['Original_Name'] = df['Name']
df['Original_Artist'] = df['Artist']

# Apply the "Clean" transformation to the primary columns
df['Name'] = df['Name'].apply(clean_text)
df['Artist'] = df['Artist'].apply(clean_text)

# Generate the Proposed Filename for the batch script
df['Clean_Filename'] = df.apply(lambda r: f"{r['Artist']} - {r['Name']}{os.path.splitext(r['Full Path'])[1]}", axis=1)

# 4. Management & OG Review Section
st.write("---")
st.subheader("📊 Step 1: Master Metadata Audit")
st.info(f"Mapping **{len(df)}** tracks. 'OG' columns added for team verification.")

# Reorder columns for the UI and the Download
# Order: Name, Artist, Album, Source, Original_Name, Original_Artist, Full Path, Clean_Filename
column_order = ['Name', 'Artist', 'Album', 'Source', 'Original_Name', 'Original_Artist', 'Full Path', 'Clean_Filename']
df_final = df[column_order]

st.dataframe(df_final.head(100), use_container_width=True, hide_index=True)

# THE MASTER CSV DOWNLOAD
st.write("---")
master_clean_csv = df_final.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Download Master Heritage Audit (CSV)",
    data=master_clean_csv,
    file_name=f"Afex_Heritage_Audit_{datetime.now().strftime('%Y%m%d')}.csv",
    mime="text/csv",
    use_container_width=True
)

# 5. THE PIECE-MEAL MIGRATOR (Disk Space Workaround)
st.write("---")
st.subheader("⚡ Step 2: Piece-meal Migration")
st.caption("Avoid D: Drive issues by moving only what you need for the next event.")

event_search = st.text_input("Search Event/Folder to migrate (e.g., 'Chilenas'):")
if event_search:
    event_df = df_final[df_final.apply(lambda r: event_search.lower() in str(r.values).lower(), axis=1)].copy()
    st.write(f"Found **{len(event_df)}** tracks for this batch.")
    
    local_root = st.text_input("Enter Local Dropbox Root (e.g., D:/Dropbox):", key="local_migrate")
    
    if local_root and st.button("🚀 Generate Migration Script"):
        local_root = local_root.replace("\\", "/").rstrip("/") + "/"
        commands = [f'New-Item -ItemType Directory -Force -Path "{local_root}Afex_Clean_Library"']
        
        for idx, row in event_df.iterrows():
            src = (local_root + row['Full Path'].lstrip("/")).replace("/", "\\")
            dest_folder = f"{local_root}Afex_Clean_Library/{re.sub(r'[\\\\/*?:\"<>|]', '', str(row['Album']))}".replace("/", "\\")
            commands.append(f'New-Item -ItemType Directory -Force -Path "{dest_folder}"')
            dest_file = f"{dest_folder}\\{row['Clean_Filename']}"
            commands.append(f'Copy-Item -Path "{src}" -Destination "{dest_file}" -Force -ErrorAction SilentlyContinue')
        
        st.download_button(
            label="📥 Download Batch Script",
            data="\n".join(commands),
            file_name=f"Batch_Clean_{event_search.replace(' ', '_')}.ps1",
            mime="text/plain"
        )
