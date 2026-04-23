import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime
from afexcloud.layout import bootstrap_page
from afexcloud.utils import advanced_normalize
from spotify_utils import process_exportify_csv

# 1. Page Config
st.set_page_config(page_title="DNA Processor | AfexCloud", page_icon="🌉", layout="wide")
bootstrap_page()

# 2. Key Conversion Helper
def get_camelot(key_num, mode):
    """Converts Spotify numeric Key/Mode to Camelot (e.g., 8, 1 -> 9B)."""
    keys = {0: '8', 1: '3', 2: '10', 3: '5', 4: '12', 5: '7', 6: '2', 7: '9', 8: '4', 9: '11', 10: '6', 11: '1'}
    suffix = "B" if mode == 1 else "A"
    return f"{keys.get(key_num, '?')}{suffix}"

# 3. Tool Logic
st.title("🌉 DNA Processor (Universal Bridge)")

if st.button("🔄 Reset & Start New Ingestion"):
    st.rerun()

st.info("🧬 **Flagship Mode**: Marrying high-fidelity Spotify metadata to your local collection.")

# --- STEP-BY-STEP UPLOADER ---
c1, c2 = st.columns(2)
with c1:
    # UPDATED: More descriptive header for newbies
    st.subheader("1. Metadata Source from Exportify File")
    st.caption("This file provides the BPM and Camelot Keys Spotify now hides.")
    exp_f = st.file_uploader("Drop Exportify CSV here", type=["csv"], key="exp_src", label_visibility="collapsed")
with c2:
    # UPDATED: More descriptive header for newbies
    st.subheader("2. Local Files from Mp3Tag File")
    st.caption("This file is your current library inventory exported from Mp3Tag.")
    loc_f = st.file_uploader("Drop Mp3Tag CSV here", type=["csv"], key="loc_src", label_visibility="collapsed")

if exp_f and loc_f:
    try:
        with st.spinner("🔗 Linking files and injecting metadata..."):
            # A. Process Exportify Side
            df_exp = process_exportify_csv(exp_f)
            df_exp = df_exp.rename(columns={'Key': 'Key_Num', 'Mode': 'Mode_Num'})
            df_exp['Camelot_Source'] = df_exp.apply(lambda r: get_camelot(r.get('Key_Num', 0), r.get('Mode_Num', 1)), axis=1)
            
            # Create Triple-Match Key for accuracy
            df_exp["match_key"] = df_exp.apply(
                lambda r: f"{advanced_normalize(r['Name'])}__{advanced_normalize(r['Artist'])}__{advanced_normalize(r['Album'])}", 
                axis=1
            )

            # B. Process Local Side (MP3Tag)
            df_loc = pd.read_csv(loc_f)
            df_loc["match_key"] = df_loc.apply(
                lambda r: f"{advanced_normalize(str(r.iloc[0]))}__{advanced_normalize(str(r.iloc[1]))}__{advanced_normalize(str(r.iloc[2]))}" 
                if len(r) >= 3 else "", axis=1
            )

            # C. THE MARRIAGE
            enriched_df = pd.merge(df_loc, df_exp[['match_key', 'BPM', 'Camelot_Source', 'Spotify-id']], on='match_key', how='left')

            # D. THE FLAGGING SYSTEM
            enriched_df['Flag'] = enriched_df['BPM'].apply(lambda x: "✅ Enriched" if pd.notnull(x) else "🚩 Missing")

            # E. UI Cleanup
            enriched_df = enriched_df.rename(columns={
                enriched_df.columns[0]: 'Name',
                enriched_df.columns[1]: 'Artist',
                enriched_df.columns[2]: 'Album',
                'Camelot_Source': 'Camelot',
                'Spotify-id': 'Spotify ID'
            })
            
            display_cols = ['Flag', 'Name', 'Artist', 'Album', 'BPM', 'Camelot', 'Spotify ID']
            final_df = enriched_df[display_cols].copy()
            final_df['BPM'] = final_df['BPM'].fillna(0).astype(int).astype(str)
            final_df['Camelot'] = final_df['Camelot'].fillna("N/A")

            # F. Visual Metrics Dashboard
            m_count = (final_df['Flag'] == "🚩 Missing").sum()
            e_count = len(final_df) - m_count
            
            m1, m2 = st.columns(2)
            m1.metric("Tracks Enriched", e_count)
            m2.metric("Metadata Mismatches", m_count, delta_color="inverse")

            # G. MAIN DISPLAY
            st.write("### 💎 Enriched Master DJ Log")
            st.data_editor(
                final_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Flag": st.column_config.TextColumn(width="medium"),
                    "BPM": st.column_config.TextColumn(),
                }
            )

            # H. DYNAMIC MASTER DOWNLOAD
            safe_proj = st.session_state.get("_safe_proj", "Project")
            p_name_raw = exp_f.name.rsplit('.', 1)[0]
            clean_p_name = re.sub(r'[^a-zA-Z0-9_]', '_', p_name_raw)
            timestamp = datetime.now().strftime("%Y%m%d")
            
            # KAIZEN: utf-8-sig ensures emojis render correctly in Excel
            st.download_button(
                label=f"📥 Save Enriched Master Log for {p_name_raw}",
                data=final_df.to_csv(index=False).encode('utf-8-sig'),
                file_name=f"DNA_Enriched_{safe_proj}_{clean_p_name}.csv",
                mime="text/csv",
                use_container_width=True
            )

    except Exception as e:
        st.error(f"Bridge connection failed: {e}")
