import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime
from afexcloud.layout import bootstrap_page

# 1. Page Config
st.set_page_config(page_title="Auto-Rename | AfexCloud", page_icon="🏗️", layout="wide")
bootstrap_page()

st.title("🏗️ Afex Library Architect")
st.caption("Safe Reconstruction | Original Files Protected | Evans/Greeley HQ")

# 2. Logic Check
if 'cloud_inventory' not in st.session_state:
    st.error("🚨 **Inventory Missing**: Run a scan in 'Dropbox Bridge' (Page 13) first.")
    st.stop()

df = st.session_state['cloud_inventory']

st.write("---")
st.subheader("🛠️ Step 1: Destination Mapping")
local_root = st.text_input(
    "Enter your local Dropbox path (e.g., D:/Dropbox or C:/Users/Admin/Dropbox):",
    placeholder="Where should we build the Clean Library?"
)

if local_root:
    local_root = local_root.replace("\\", "/").rstrip("/") + "/"
    st.info(f"The new library will be built at: `{local_root}Afex_Clean_Library/`")

    # 3. Create the Proposed Mapping
    def get_clean_filename(row):
        artist = re.sub(r'[\\/*?:"<>|]', "", str(row['Artist']))
        name = re.sub(r'[\\/*?:"<>|]', "", str(row['Name']))
        ext = os.path.splitext(row['Full Path'])[1]
        return f"{artist} - {name}{ext}"

    df['New_Filename'] = df.apply(get_clean_filename, axis=1)
    
    st.write("---")
    st.subheader("📝 Step 2: Review Reconstruction")
    st.dataframe(df[['Name', 'Artist', 'Album', 'New_Filename']].head(100), use_container_width=True, hide_index=True)

    # 4. Generate PowerShell Script
    st.write("---")
    st.subheader("🚀 Step 3: Generate Reconstruction Script")
    
    # --- THE REQUESTED REMINDER BOX ---
    st.warning("""
        ### ⚠️ CRITICAL NEXT STEP FOR ALL USERS
        Once you run the downloaded script on your computer, your clean music will live in a new folder. 
        
        **To see the clean data in the future:** Go back to the **Dropbox Bridge (Page 13)** and simply type: 
        `/Afex_Clean_Library` 
        into the **Folder Path** box before you scan.
    """)

    commands = []
    commands.append(f'New-Item -ItemType Directory -Force -Path "{local_root}Afex_Clean_Library"')

    unique_folders = df['Album'].unique()
    for folder in unique_folders:
        folder_clean = re.sub(r'[\\/*?:"<>|]', "", str(folder))
        commands.append(f'New-Item -ItemType Directory -Force -Path "{local_root}Afex_Clean_Library/{folder_clean}"')

    for idx, row in df.iterrows():
        src = (local_root + row['Full Path'].lstrip("/")).replace("/", "\\")
        folder_clean = re.sub(r'[\\/*?:"<>|]', "", str(row['Album']))
        dest = f"{local_root}Afex_Clean_Library/{folder_clean}/{row['New_Filename']}".replace("/", "\\")
        commands.append(f'Copy-Item -Path "{src}" -Destination "{dest}" -Force -ErrorAction SilentlyContinue')

    full_script = "\n".join(commands)

    st.download_button(
        label=f"📥 Download Reconstruction Script ({len(df)} files)",
        data=full_script,
        file_name=f"Afex_Reconstruct_Library_{datetime.now().strftime('%Y%m%d')}.ps1",
        mime="text/plain",
        use_container_width=True
    )

# --- INSTRUCTIONS ---
st.write("---")
with st.expander("📖 Step-by-Step Instructions"):
    st.write("""
    1. **Download**: Click the big button above to get your `.ps1` script.
    2. **Run**: Find the file on your computer, right-click it, and select **'Run with PowerShell'**.
    3. **Verify**: Open your Dropbox and look for the `Afex_Clean_Library` folder.
    4. **Switch Over**: Use that new folder path in Page 13 for all future audits.
    """)
