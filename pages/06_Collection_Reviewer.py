import streamlit as st
import pandas as pd
import sys
import os
import re
from datetime import datetime

# Path Fix for 'pages' folder access
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from afexcloud.layout import bootstrap_page
from afexcloud.utils import advanced_normalize
from spotify_utils import process_exportify_csv_trimmed

# 1. Page Config
st.set_page_config(page_title="Collection Reviewer | AfexCloud", page_icon="📊", layout="wide")

# 2. Bootstrap Style & Security
auth_manager, token_info = bootstrap_page()

# 3. Tool Logic
st.title("📊 Collection Reviewer (Purified)")

# --- NEWBIE GUIDE ---
with st.expander("🆕 How to run a QC Review", expanded=True):
    st.markdown("""
    This tool performs a **Triple-Match** (Title, Artist, and Album) to verify your library.
    1.  **Spotify Inventory**: Upload the Exportify CSV (it will be trimmed automatically).
    2.  **Local Library**: Upload your local database CSV (e.g., exported from Serato or your internal drive).
    3.  **Review**: The tool will show you what is 'Safe' and what needs your attention.
    """)
    st.link_button("🔗 Go to Exportify.net", "https://exportify.net/")

st.write("---")

c1, c2 = st.columns(2)
with c1:
    st.subheader("1. Spotify Inventory")
    inv_f = st.file_uploader("Upload Exportify CSV", type="csv", key="inv")
with c2:
    st.subheader("2. Local Library")
    loc_f = st.file_uploader("Upload Local DB CSV", type="csv", key="loc")

if inv_f and loc_f:
    if st.button("📊 Generate Smart Review"):
        with st.spinner("Analyzing library alignment..."):
            # A. Process Spotify Side (The Trimmed Ground Truth)
            df_inv = process_exportify_csv_trimmed(inv_f)
            
            # Create a Triple-Match Key for Spotify
            df_inv["match_key"] = df_inv.apply(
                lambda r: f"{advanced_normalize(r['Name'])}__{advanced_normalize(r['Artist'])}__{advanced_normalize(r['Album'])}", 
                axis=1
            )

            # B. Process Local Side
            # Logic assumes local CSV has headers or uses comma-separated 'Song,Artist,Album'
            df_loc = pd.read_csv(loc_f)
            
            # Creating local keys (Flexible logic to find the right columns)
            # We look for columns that 'look like' Name, Artist, and Album
            df_loc["match_key"] = df_loc.apply(
                lambda r: f"{advanced_normalize(str(r.iloc[0]))}__{advanced_normalize(str(r.iloc[1]))}__{advanced_normalize(str(r.iloc[2]))}" 
                if len(r) >= 3 else "", axis=1
            )
            local_keys = set(df_loc["match_key"].tolist())

            # C. Perform the Audit
            df_inv["Status"] = df_inv["match_key"].apply(lambda k: "✅ Exact Match" if k in local_keys else "❌ Missing Version")

            # D. Display Dashboard
            match_count = (df_inv["Status"] == "✅ Exact Match").sum()
            missing_count = len(df_inv) - match_count
            
            m1, m2 = st.columns(2)
            m1.metric("Library Alignment", f"{int((match_count/len(df_inv))*100)}%")
            m2.metric("Missing from Local", missing_count, delta_color="inverse")

            # E. Results Table
            st.write("### Detailed Inventory Review")
            # We only show the columns requested: Pos, Name, Artist, Album, and our new Status
            final_df = df_inv[['Status', 'Pos', 'Name', 'Artist', 'Album']]
            st.dataframe(final_df, use_container_width=True, hide_index=True)

            # F. Download the "Purified" Report
            safe_proj = st.session_state.get("global_proj", "Project")
            timestamp = datetime.now().strftime("%Y%m%d")
            
            st.download_button(
                label="📥 Download Purified Review Report",
                data=final_df.to_csv(index=False).encode('utf-8'),
                file_name=f"AfexCloud_{safe_proj}_QC_Review_{timestamp}.csv",
                mime="text/csv"
            )
