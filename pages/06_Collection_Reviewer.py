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

st.title("📊 Collection Reviewer")

# --- NEWBIE GUIDE ---
with st.expander("🆕 How to identify missing songs", expanded=False):
    st.markdown("""
    1. **Spotify Inventory**: Upload the Exportify CSV.
    2. **Local Library**: Upload your MP3Tag report (Title, Artist, Album, BPM, Key).
    3. **Missing Tracks**: View the specific songs that didn't find a match below the main table.
    """)

st.write("---")

c1, c2 = st.columns(2)
with c1:
    inv_f = st.file_uploader("1. Spotify Inventory (Exportify)", type="csv")
with c2:
    loc_f = st.file_uploader("2. Local Library (MP3Tag)", type="csv")

if inv_f and loc_f:
    if st.button("📊 Run Deep Audit"):
        with st.spinner("Comparing libraries..."):
            # A. Process Spotify Side
            df_inv = process_exportify_csv_trimmed(inv_f)
            df_inv["match_key"] = df_inv.apply(
                lambda r: f"{advanced_normalize(r['Name'])}__{advanced_normalize(r['Artist'])}__{advanced_normalize(r['Album'])}", 
                axis=1
            )

            # B. Process Local Side (MP3Tag CSV)
            df_loc = pd.read_csv(loc_f)
            # Match keys based on the MP3Tag Export Configuration we built
            df_loc["match_key"] = df_loc.apply(
                lambda r: f"{advanced_normalize(str(r.iloc[0]))}__{advanced_normalize(str(r.iloc[1]))}__{advanced_normalize(str(r.iloc[2]))}" 
                if len(r) >= 3 else "", axis=1
            )
            local_keys = set(df_loc["match_key"].tolist())

            # C. Perform Audit
            df_inv["Status"] = df_inv["match_key"].apply(lambda k: "✅ Match" if k in local_keys else "❌ Missing")

            # D. Metrics Summary
            missing_df = df_inv[df_inv["Status"] == "❌ Missing"].copy()
            match_rate = int(( (len(df_inv) - len(missing_df)) / len(df_inv) ) * 100)
            
            m1, m2 = st.columns(2)
            m1.metric("Library Alignment", f"{match_rate}%")
            m2.metric("Missing from Local", len(missing_df), delta_color="inverse")

            # E. Detailed Table
            st.write("### 📋 Full Inventory Status")
            st.dataframe(df_inv.drop(columns=['match_key']), use_container_width=True, hide_index=True)

            # F. NEW: Missing Tracks Section
            st.write("---")
            if not missing_df.empty:
                st.subheader(f"🚩 Tracks Missing from Local ({len(missing_df)})")
                st.info("The following songs are in the Spotify playlist but were NOT found in your MP3Tag report.")
                
                # Show Pos, Name, Artist, Album, BPM, Key for easy locating
                st.dataframe(missing_df.drop(columns=['Status', 'match_key']), use_container_width=True, hide_index=True)
                
                # Download report of just the missing songs
                safe_proj = st.session_state.get("global_proj", "Project")
                st.download_button(
                    "📥 Download Missing Tracks List",
                    data=missing_df.to_csv(index=False).encode('utf-8'),
                    file_name=f"AfexCloud_{safe_proj}_MISSING_REPORT.csv",
                    mime="text/csv"
                )
            else:
                st.success("Perfect Match! All Spotify songs were found in your local collection.")

            # G. "Lone Wolf" Check (Optional: Extras in Local)
            extra_local = df_loc[~df_loc["match_key"].isin(df_inv["match_key"])]
            if not extra_local.empty:
                with st.expander(f"📂 View {len(extra_local)} 'Extra' songs in this folder"):
                    st.write("These files are in your local folder but are NOT in the Spotify playlist.")
                    st.dataframe(extra_local.iloc[:, :3], use_container_width=True, hide_index=True)
