import streamlit as st
import pandas as pd
import sys
import os
import re
from datetime import datetime

# Path Fix for 'pages' folder access
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from afexcloud.layout import bootstrap_page
from spotify_utils import process_exportify_csv

# 1. Page Config - Designed for Small Sidebar real estate
st.set_page_config(page_title="Lister '26 | AfexCloud", page_icon="⚡", layout="wide")

# 2. Bootstrap Style & Security
auth_manager, token_info = bootstrap_page()

# 3. Tool Logic
st.title("⚡ Lister '26 (Beta)")
st.caption("Kaizen Edition: Drag, Drop, and Presto.")

# THE AUTO-INGEST ZONE
# This is the 'One-Button' replacement. 
# As soon as the file hits this zone, Streamlit triggers the code below.
uploaded_file = st.file_uploader("🚀 Drag Exportify CSV Here", type=["csv"], label_visibility="collapsed")

if uploaded_file:
    # 1. Auto-Extract Playlist Identity
    raw_name = uploaded_file.name.rsplit('.', 1)[0]
    clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', raw_name)
    
    with st.status(f"Ingesting {raw_name}...", expanded=False) as status:
        # 2. Behind-the-Scenes Processing
        # Uses your fixed spotify_utils for decimal-free BPM
        df = process_exportify_csv(uploaded_file)
        
        # 3. Auto-Assignment of Positions
        df.insert(0, 'Pos', range(1, len(df) + 1))
        df['BPM'] = df['BPM'].astype(str)
        
        status.update(label="Ingestion Complete!", state="complete")

    # 4. Instant Display
    st.subheader(f"📋 {raw_name} Inventory")
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # 5. One-Click Professional Download
    safe_proj = st.session_state.get("global_proj", "Project")
    timestamp = datetime.now().strftime("%y%m%d")
    
    st.download_button(
        label=f"📥 Save Cleaned {clean_name}",
        data=df.to_csv(index=False).encode('utf-8'),
        file_name=f"Afex_{safe_proj}_{clean_name}_{timestamp}.csv",
        mime="text/csv",
        use_container_width=True
    )
    
    st.toast(f"Successfully purified {len(df)} tracks!", icon="✅")

else:
    # Minimalist Landing for Newbies
    st.info("💡 **Kaizen Tip:** Click 'Export' on Exportify, then drag the file from your browser's bottom bar directly into the space above.")
    st.link_button("🔗 Open Exportify.net", "https://exportify.net/")
