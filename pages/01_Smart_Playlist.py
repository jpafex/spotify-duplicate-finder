import streamlit as st
import pandas as pd
import os  # <--- Make sure this line is at the very top!

# Page Configuration
st.set_page_config(
    page_title="ProDJ Smart Playlist Generator", 
    page_icon="🎧", 
    layout="wide"
)

# App Header
st.title("🎧 ProDJ Enterprise Harmonic Flow Engine")
st.markdown("Transform raw client tracklists into seamlessly blended, mathematically optimized event setlists.")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Curator Controls")
st.sidebar.markdown("Adjust algorithmic weighting for the event profile.")

bpm_weight = st.sidebar.slider(
    "Tempo (BPM) Strictness", 
    min_value=0.1, max_value=2.0, value=0.5, step=0.1,
    help="Higher values force songs to stay closer in tempo."
)

harmonic_penalty_val = st.sidebar.slider(
    "Key Incompatibility Penalty", 
    min_value=1, max_value=20, value=10, step=1,
    help="Higher values heavily penalize non-harmonious key transitions."
)

# --- MAIN INTERFACE ---
uploaded_file = st.file_uploader("Upload Raw Spotify Playlist (.csv)", type=["csv"])

if uploaded_file is not None:
    # 1. Load data
    df = pd.read_csv(uploaded_file)
    
    # 2. Standardize headers & clean tempo
    col_mapping = {col: col.title() for col in df.columns}
    df = df.rename(columns=col_mapping)
    if 'Bpm' in df.columns:
        df = df.rename(columns={'Bpm': 'Tempo'})
        
    if 'Tempo' in df.columns:
        df['Tempo'] = df['Tempo'].round(0).astype(int)

    # 3. AUTOMATIC MAGIC: Calculate Camelot Key and Relative (Alt) Key right away!
    major_map = {11: '1B', 6: '2B', 1: '3B', 8: '4B', 3: '5B', 10: '6B', 5: '7B', 0: '8B', 7: '9B', 2: '10B', 9: '11B', 4: '12B'}
    minor_map = {8: '1A', 3: '2A', 10: '3A', 5: '4A', 0: '5A', 7: '6A', 2: '7A', 9: '8A', 4: '9A', 11: '10A', 6: '11A', 1: '12A'}
    
    def get_camelot(row):
        if pd.isna(row.get('Key')) or pd.isna(row.get('Mode')):
            return 'Unknown'
        return major_map.get(int(row['Key']), 'Unknown') if row['Mode'] == 1 else minor_map.get(int(row['Key']), 'Unknown')

    df['Camelot Key'] = df.apply(get_camelot, axis=1)
    df['Relative Key (Alt)'] = df['Camelot Key'].apply(
        lambda x: x.replace('A', 'B') if 'A' in x else (x.replace('B', 'A') if 'B' in x else 'Unknown')
    )

    # Display Preview
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Raw Upload Preview (Auto-Processed)")
        st.write(f"Total Tracks Loaded: {len(df)}")
        preview_cols = [c for c in ['Track Name', 'Tempo', 'Camelot Key', 'Relative Key (Alt)'] if c in df.columns]
        st.dataframe(df.head(3)[preview_cols], use_container_width=True)
        
    with col2:
        st.subheader("Event Parameters")
        st.info("Keys and relative alternatives have been automatically computed. Ready for optimization.")

    if st.button("🚀 Generate Optimized Setlist", type="primary"):
        with st.spinner("Analyzing track metadata and calculating optimal mix path..."):
            
            def score_transition(t1, t2):
                if 'Tempo' not in t1 or 'Tempo' not in t2:
                    return 0
                bpm_diff = abs(t1['Tempo'] - t2['Tempo'])
                bpm_p = bpm_diff * bpm_weight
                
                k1, k2 = str(t1['Camelot Key']), str(t2['Camelot Key'])
                if k1 == 'Unknown' or k2 == 'Unknown':
                    return 100
                
                num1, let1 = int(k1[:-1]), k1[-1]
                num2, let2 = int(k2[:-1]), k2[-1]
                
                h_penalty = harmonic_penalty_val
                if k1 == k2:
                    h_penalty = 0
                elif num1 == num2 and let1 != let2:
                    h_penalty = 1
                elif let1 == let2 and (abs(num1 - num2) == 1 or abs(num1 - num2) == 11):
                    h_penalty = 1
                    
                return bpm_p + h_penalty

            unplayed = df.to_dict('records')
            sorted_playlist = [unplayed.pop(0)]
            
            while unplayed:
                current = sorted_playlist[-1]
                best_next = None
                best_score = float('inf')
                for track in unplayed:
                    score = score_transition(current, track)
                    if score < best_score:
                        best_score = score
                        best_next = track
                sorted_playlist.append(best_next)
                unplayed.remove(best_next)
                
            result_df = pd.DataFrame(sorted_playlist)
            
            # --- STAMP THE CURATOR CONTROLS INTO THE DATAFRAME ---
            # Format BPM weight nicely (e.g., 1.60 becomes "160" or keep as formatted string)
            bpm_str = f"{int(bpm_weight * 100):03d}"  # e.g., 1.60 -> "160"
            penalty_str = str(int(harmonic_penalty_val)) # e.g., 13 -> "13"
            
            result_df['BPM_Strictness'] = bpm_weight
            result_df['Key_Penalty'] = harmonic_penalty_val

        st.success("Setlist successfully generated and stamped!")
        
        # Display Final Table (including the parameter audit columns)
        st.subheader("✨ Optimized Transition Flow")
        show_cols = [c for c in ['Track Name', 'Artist Name(s)', 'Tempo', 'Camelot Key', 'Relative Key (Alt)', 'BPM_Strictness', 'Key_Penalty'] if c in result_df.columns]
        st.dataframe(result_df[show_cols], use_container_width=True)
        
        # --- EXTRACT PLAYLIST NAME & DYNAMICALLY FORMAT FILENAME ---
        playlist_name = os.path.splitext(uploaded_file.name)[0]
        
        bpm_str = f"{int(bpm_weight * 100):03d}"  # e.g., 1.60 -> "160"
        penalty_str = str(int(harmonic_penalty_val)) # e.g., 13 -> "13"
        
        # Result example: DJDocB_Optimized_160-13.csv
        file_name_dynamic = f"{playlist_name}_Optimized_{bpm_str}-{penalty_str}.csv"
        
        # Download Option with the smart filename
        csv_export = result_df[show_cols].to_csv(index=False).encode('utf-8')
        st.download_button(
            label=f"📥 Download Final Client Setlist ({file_name_dynamic})",
            data=csv_export,
            file_name=file_name_dynamic,
            mime="text/csv"
        
        )
else:
    st.info("👆 Upload your raw Spotify CSV file above to begin.")
