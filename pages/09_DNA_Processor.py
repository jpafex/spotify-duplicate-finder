import streamlit as st
import pandas as pd
import re
from datetime import datetime
from afexcloud.layout import bootstrap_page

# 1. Page Config
st.set_page_config(page_title="DNA Processor | AfexCloud", page_icon="🌉", layout="wide")

# 2. Bootstrap Style
bootstrap_page()

# 3. Tool Logic
st.title("🌉 DNA Processor (The Bridge)")
st.info("The 'Nutcracker' workaround is complete. Local Git Bash data is now fully integrated.")

uploaded_file = st.file_uploader("📤 Upload Local Bash Results (test_playlist_full.csv)", type="csv")

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        
        # --- SMART MAPPING FOR LOCAL BASH DATA ---
        mapping = {
            'track_name': 'Name',
            'artists': 'Artist',
            'key': 'Key',
            'bpm': 'BPM',
            'camelot': 'Camelot',
            'tempo_category': 'Tempo',
            'track_id': 'Spotify ID'
        }
        
        # Rename columns to AfexCloud standards
        df = df.rename(columns={k: v for k, v in mapping.items() if k in df.columns})
        
        # Verify the minimum requirements
        required = ['Name', 'Artist', 'Key', 'BPM']
        if not all(col in df.columns for col in required):
            st.error(f"Missing required columns. Found: {list(df.columns)}")
        else:
            # Create a clickable Web Link for the browser
            if 'Spotify ID' in df.columns:
                df['Web Player'] = df['Spotify ID'].apply(lambda x: f"https://open.spotify.com/track/{x}")

            # Reorder for the 'Lark View'
            main_cols = ['Name', 'Artist', 'Key', 'Camelot', 'BPM', 'Tempo', 'Web Player']
            other_cols = [c for c in df.columns if c not in main_cols]
            final_df = df[main_cols + other_cols]

            st.success(f"Successfully integrated {len(df)} tracks into the cloud dashboard!")

            # --- INTERACTIVE TABLE OF SORTS ---
            st.data_editor(
                final_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Web Player": st.column_config.LinkColumn(display_text="Open in Spotify"),
                    "BPM": st.column_config.NumberColumn(format="%d")
                }
            )
            
            # --- PROJECT DOWNLOAD ---
            st.write("---")
            safe_proj = st.session_state.get("_safe_proj", "Project")
            out_name = f"{safe_proj}_Master_DJ_Log_{datetime.now().strftime('%Y%m%d')}.csv"
            
            st.download_button(
                "📥 Download Master DJ Log",
                final_df.to_csv(index=False).encode('utf-8'),
                out_name,
                "text/csv"
            )

    except Exception as e:
        st.error(f"Bridge connection failed: {e}")
