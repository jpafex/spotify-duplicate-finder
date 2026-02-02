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
st.info("The engine now automatically maps 'track_name' to 'Name' and 'artists' to 'Artist'. Upload your local CSV below.")

uploaded_file = st.file_uploader("📤 Upload Local Bash Results (CSV)", type="csv")

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        
        # --- SMART MAPPING LOGIC ---
        # We look for common variations and rename them to our AfexCloud standards
        mapping = {
            'track_name': 'Name',
            'artists': 'Artist',
            'key': 'Key',
            'bpm': 'BPM',
            'camelot': 'Camelot Code',
            'track_id': 'Spotify ID'
        }
        
        # Only rename columns that actually exist in the uploaded file
        df = df.rename(columns={k: v for k, v in mapping.items() if k in df.columns})
        
        # Verify the minimum requirements are met after mapping
        required = ['Name', 'Artist', 'Key', 'BPM']
        if not all(col in df.columns for col in required):
            st.error(f"Missing required data. The CSV must contain at least: Name, Artist, Key, and BPM.")
            st.write("Columns found in your file:", list(df.columns))
        else:
            st.success(f"Successfully integrated {len(df)} tracks from your local analysis!")
            
            # Reorder columns to put the most important ones first
            display_cols = ['Name', 'Artist', 'Key', 'BPM']
            if 'Camelot Code' in df.columns: display_cols.append('Camelot Code')
            if 'Spotify ID' in df.columns: display_cols.append('Spotify ID')
            
            # Add any other columns from the local script at the end
            remaining = [c for c in df.columns if c not in display_cols]
            final_df = df[display_cols + remaining]

            # --- THE INTERACTIVE TABLE ---
            st.subheader("📊 Integrated Master DJ Log")
            st.data_editor(
                final_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "BPM": st.column_config.NumberColumn(format="%d"),
                }
            )
            
            # --- MASTER PROJECT DOWNLOAD ---
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
        st.error(f"Processing failed: {e}")
