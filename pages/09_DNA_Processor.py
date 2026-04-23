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

if st.button("🔄 Reset & Upload New Project"):
    st.rerun()

st.info("🧬 **Flagship Mode**: Enriching local files with Spotify Metadata & Flagging mismatches.")

# TWO-STAGE UPLOADER
c1, c2 = st.columns(2)
with c1:
    st.subheader("1. Metadata Source")
    exp_f = st.file_uploader("Upload Exportify CSV (BPM/Key Source)", type=["csv"])
with c2:
    st.subheader("2. Local Files")
    loc_f = st.file_uploader("Upload MP3Tag CSV (Target)", type=["csv"])

if exp_f and loc_f:
    try:
        with st.spinner("Executing metadata marriage & analysis..."):
            # A. Process Exportify Side
            df_exp = process_exportify_csv(exp_f)
            
            # Map Mode and Key for Camelot generation
            df_exp = df_exp.rename(columns={'Key': 'Key_Num', 'Mode': 'Mode_Num'})
            df_exp['Camelot_Source'] = df_exp.apply(lambda r: get_camelot(r.get('Key_Num', 0), r.get('Mode_Num', 1)), axis=1)
            
            # Create Triple-Match Key
            df_exp["match_key"] = df_exp.apply(
                lambda r: f"{advanced_normalize(r['Name'])}__{advanced_normalize(r['Artist'])}__{advanced_normalize(r['Album'])}", 
                axis=1
            )

            # B. Process Local Side (MP3Tag)
            df_loc = pd.read_csv(loc_f)
            # Match keys based on MP3Tag positions (Title, Artist, Album)
            df_loc["match_key"] = df_loc.apply(
                lambda r: f"{advanced_normalize(str(r.iloc[0]))}__{advanced_normalize(str(r.iloc[1]))}__{advanced_normalize(str(r.iloc[2]))}" 
                if len(r) >= 3 else "", axis=1
            )

            # C. THE MARRIAGE (Left Join)
            # Keeping all local rows; unmatched Spotify columns will be NaN
            enriched_df = pd.merge(
                df_loc, 
                df_exp[['match_key', 'BPM', 'Camelot_Source', 'Spotify-id']], 
                on='match_key', 
                how='left'
            )

            # D. THE FLAGGING SYSTEM
            # If BPM or Camelot is missing from the join, it's a mismatch
            enriched_df['Flag'] = enriched_df['BPM'].apply(lambda x: "✅ Enriched" if pd.notnull(x) else "🚩 Missing Metadata")

            # E. UI Cleanup
            enriched_df = enriched_df.rename(columns={
                enriched_df.columns[0]: 'Name',
                enriched_df.columns[1]: 'Artist',
                enriched_df.columns[2]: 'Album',
                'Camelot_Source': 'Camelot',
                'Spotify-id': 'Spotify ID'
            })
            
            # Display Columns
            display_cols = ['Flag', 'Name', 'Artist', 'Album', 'BPM', 'Camelot', 'Spotify ID']
            final_df = enriched_df[display_cols].copy()
            
            # Format BPM for clear display
            final_df['BPM'] = final_df['BPM'].fillna(0).astype(int).astype(str)
            final_df['Camelot'] = final_df['Camelot'].fillna("N/A")

            # F. Metrics Dashboard
            m_count = (final_df['Flag'] == "🚩 Missing Metadata").sum()
            e_count = len(final_df) - m_count
            
            m1, m2 = st.columns(2)
            m1.metric("Enriched Successfully", e_count)
            m2.metric("Flags (Mismatches)", m_count, delta_color="inverse")

            # G. MAIN DISPLAY: The Master Enriched Log
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

            # H. THE FLAG REPORT: Isolated Missing Data
            if m_count > 0:
                with st.expander(f"🚩 View {m_count} tracks that failed to find metadata", expanded=True):
                    st.warning("These local files did not match the Spotify Inventory. Check for album name differences or missing remixes.")
                    flagged_df = final_df[final_df['Flag'] == "🚩 Missing Metadata"].drop(columns=['Flag'])
                    st.dataframe(flagged_df, use_container_width=True, hide_index=True)

            # I. DYNAMIC MASTER DOWNLOAD
            safe_proj = st.session_state.get("_safe_proj", "Project")
            p_name_raw = exp_f.name.rsplit('.', 1)[0]
            clean_p_name = re.sub(r'[^a-zA-Z0-9_]', '_', p_name_raw)
            timestamp = datetime.now().strftime("%Y%m%d")
            
            st.download_button(
                label=f"📥 Download Enriched & Flagged Log ({p_name_raw})",
                data=final_df.to_csv(index=False).encode('utf-8'),
                file_name=f"DNA_Enriched_{safe_proj}_{clean_p_name}_{timestamp}.csv",
                mime="text/csv",
                use_container_width=True
            )

    except Exception as e:
        st.error(f"Metadata marriage failed: {e}")
