import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import datetime
from afexcloud.layout import bootstrap_page

# 1. Page Config
st.set_page_config(page_title="DNA Processor | AfexCloud", page_icon="🌉", layout="wide")
bootstrap_page()

# 2. Helper Functions
def get_camelot(key_num, mode):
    """Converts Spotify numeric Key/Mode to Camelot (e.g., 8, 1 -> 9B)."""
    # Mapping based on standard DJ Camelot wheel logic
    keys = {0: '8', 1: '3', 2: '10', 3: '5', 4: '12', 5: '7', 6: '2', 7: '9', 8: '4', 9: '11', 10: '6', 11: '1'}
    suffix = "B" if mode == 1 else "A"
    return f"{keys.get(key_num, '?')}{suffix}"

# 3. Tool Logic
st.title("🌉 DNA Processor (The Universal Bridge)")

# RESET BUTTON: Placed at the top for quick access during multi-playlist sessions
if st.button("🔄 Reset Tool & Upload New File"):
    st.rerun()

st.info("2026 Dovetail Active: Unifying Exportify and Local Bash data into a Descriptive DJ Log.")

# 4. Universal Ingestor
uploaded_file = st.file_uploader("📤 Upload CSV (Exportify or Local Bash)", type=["csv"], label_visibility="collapsed")

if uploaded_file:
    # EXTRACT PLAYLIST NAME: Captures 'Chilenas' from 'Chilenas.csv' for naming
    raw_playlist_name = uploaded_file.name.rsplit('.', 1)[0]
    clean_p_name = re.sub(r'[^a-zA-Z0-9_]', '_', raw_playlist_name)
    
    try:
        df = pd.read_csv(uploaded_file)
        
        # --- THE UNIVERSAL MAPPER ---
        # Maps both Local Bash and Exportify headers to Afex Standards
        mapping = {
            'track_name': 'Name',
            'artists': 'Artist',
            'track_id': 'Spotify ID',
            'tempo_category': 'Tempo_Cat',
            'camelot': 'Camelot',
            'Track Name': 'Name',
            'Artist Name(s)': 'Artist',
            'Album Name': 'Album',
            'Track URI': 'Spotify ID',
            'Tempo': 'BPM',
            'Key': 'Key_Num',
            'Mode': 'Mode_Num'
        }
        
        df = df.rename(columns={k: v for k, v in mapping.items() if k in df.columns})
        
        # BPM DECIMAL ANNIHILATION: Keeps it clean for DJ eyes
        if 'BPM' in df.columns:
            df['BPM'] = pd.to_numeric(df['BPM'], errors='coerce').fillna(0).apply(np.floor).astype(int)
        
        # AUTO-GENERATING CAMELOT: Fills the gap for Exportify-only data
        if 'Camelot' not in df.columns and 'Key_Num' in df.columns and 'Mode_Num' in df.columns:
            df['Camelot'] = df.apply(lambda r: get_camelot(r['Key_Num'], r['Mode_Num']), axis=1)

        # 2026 WEB PLAYER LINK: Essential for quick preview in the 2026 restricted environment
        if 'Spotify ID' in df.columns:
            df['Spotify ID'] = df['Spotify ID'].apply(lambda x: str(x).split(':')[-1])
            df['Web Player'] = df['Spotify ID'].apply(lambda x: f"https://open.spotify.com/track/{x}")

        # Final Column Arrangement for 'Lark View'
        main_cols = ['Name', 'Artist', 'BPM', 'Camelot', 'Web Player']
        existing_main = [c for c in main_cols if c in df.columns]
        other_cols = [c for c in df.columns if c not in existing_main]
        final_df = df[existing_main + other_cols]

        st.success(f"Bridge Active: Unified {len(df)} tracks from '{raw_playlist_name}'")

        # --- INTERACTIVE DJ LOG EDITOR ---
        st.data_editor(
            final_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Web Player": st.column_config.LinkColumn(display_text="Open"),
                "BPM": st.column_config.NumberColumn(format="%d")
            }
        )
        
        # --- DYNAMIC PROJECT LOG DOWNLOAD ---
        st.write("---")
        safe_proj = st.session_state.get("_safe_proj", "Project")
        timestamp = datetime.now().strftime("%Y%m%d")
        
        # Dynamic Filename: Includes Project name AND Playlist name
        final_out_name = f"DNA_Master_Log_{safe_proj}_{clean_p_name}_{timestamp}.csv"
        
        st.download_button(
            label=f"📥 Download Master Log for {raw_playlist_name}",
            data=final_df.to_csv(index=False).encode('utf-8'),
            file_name=final_out_name,
            mime="text/csv",
            use_container_width=True
        )

    except Exception as e:
        st.error(f"Bridge connection failed: {e}")
