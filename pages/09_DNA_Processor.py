import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime
from afexcloud.layout import bootstrap_page

# 1. Page Config
st.set_page_config(page_title="DNA Processor | AfexCloud", page_icon="🌉", layout="wide")
bootstrap_page()

# 2. Key Conversion Helper (DJs love Camelot)
def get_camelot(key_num, mode):
    """Converts Spotify numeric Key/Mode to Camelot (e.g., 0, 1 -> 8B)."""
    # Simplified mapping for demonstration
    keys = {0: '8', 1: '3', 2: '10', 3: '5', 4: '12', 5: '7', 6: '2', 7: '9', 8: '4', 9: '11', 10: '6', 11: '1'}
    suffix = "B" if mode == 1 else "A"
    return f"{keys.get(key_num, '?')}{suffix}"

# 3. Tool Logic
st.title("🌉 DNA Processor (The Universal Bridge)")
st.info("2026 Dovetail Active: Now ingests Exportify CSVs and Local Bash data into a Unified DJ Log.")

# ONE UPLOADER - TWO PATHS
uploaded_file = st.file_uploader("📤 Upload CSV (Exportify or Local Bash)", type="csv")

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        
        # --- THE UNIVERSAL MAPPER ---
        # Combines your Local Bash headers and Exportify headers
        mapping = {
            # Local Bash Headers
            'track_name': 'Name',
            'artists': 'Artist',
            'track_id': 'Spotify ID',
            'tempo_category': 'Tempo_Cat',
            'camelot': 'Camelot',
            # Exportify Headers
            'Track Name': 'Name',
            'Artist Name(s)': 'Artist',
            'Album Name': 'Album',
            'Track URI': 'Spotify ID',
            'Tempo': 'BPM',
            'Key': 'Key_Num',
            'Mode': 'Mode_Num'
        }
        
        # Rename columns to AfexCloud standards
        df = df.rename(columns={k: v for k, v in mapping.items() if k in df.columns})
        
        # BPM DECIMAL ANNIHILATION (Kaizen Fix)
        if 'BPM' in df.columns:
            df['BPM'] = pd.to_numeric(df['BPM'], errors='coerce').fillna(0).apply(np.floor).astype(int)
        
        # AUTO-GENERATING CAMELOT (If not present in Exportify data)
        if 'Camelot' not in df.columns and 'Key_Num' in df.columns and 'Mode_Num' in df.columns:
            df['Camelot'] = df.apply(lambda r: get_camelot(r['Key_Num'], r['Mode_Num']), axis=1)

        # 2026 WEB LINK GENERATION
        if 'Spotify ID' in df.columns:
            # Clean ID from 'spotify:track:ID' if needed
            df['Spotify ID'] = df['Spotify ID'].apply(lambda x: str(x).split(':')[-1])
            df['Web Player'] = df['Spotify ID'].apply(lambda x: f"https://open.spotify.com/track/{x}")

        # Finalizing the 'Lark View' columns
        main_cols = ['Name', 'Artist', 'BPM', 'Camelot', 'Web Player']
        existing_main = [c for c in main_cols if c in df.columns]
        other_cols = [c for c in df.columns if c not in existing_main]
        final_df = df[existing_main + other_cols]

        st.success(f"Bridge Active: {len(df)} tracks unified!")

        # --- INTERACTIVE DJ LOG ---
        st.data_editor(
            final_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Web Player": st.column_config.LinkColumn(display_text="Open"),
                "BPM": st.column_config.NumberColumn(format="%d")
            }
        )
        
        # --- MASTER PROJECT LOG DOWNLOAD ---
        st.write("---")
        safe_proj = st.session_state.get("_safe_proj", "Project")
        out_name = f"DNA_Master_Log_{safe_proj}_{datetime.now().strftime('%Y%m%d')}.csv"
        
        st.download_button(
            "📥 Download Master DJ Log",
            final_df.to_csv(index=False).encode('utf-8'),
            out_name,
            "text/csv"
        )

    except Exception as e:
        st.error(f"Bridge connection failed: {e}")
