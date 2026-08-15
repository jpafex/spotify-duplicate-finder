import streamlit as st
import pandas as pd
import sys
import os
import re
import tempfile
import zipfile
import io
from pathlib import Path
from mutagen import File
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TCON, TDRC, TXXX, TKEY, TBPM

# Path Fix for accessing auth.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from afexcloud.layout import bootstrap_page

# Page Configuration
st.set_page_config(page_title="MP3 Metadata Tag Writer", page_icon="🏷️", layout="wide")

# Authentication
bootstrap_page()

st.title("🏷️ Cloud ID3 Tag Writer")
st.markdown("Upload a CSV of track data and a `.zip` archive of your raw MP3s. The engine will match them, rewrite the ID3 tags, and bundle them back up for download.")

# --- CORE FUNCTIONS ---
def convert_spotify_key_to_camelot(spotify_key, mode):
    major_map = {0:'8B',1:'3B',2:'10B',3:'5B',4:'12B',5:'7B',6:'2B',7:'9B',8:'4B',9:'11B',10:'6B',11:'1B'}
    minor_map = {0:'5A',1:'12A',2:'7A',3:'2A',4:'9A',5:'4A',6:'11A',7:'6A',8:'1A',9:'8A',10:'3A',11:'10A'}
    return major_map.get(spotify_key, 'Unknown') if mode == 1 else minor_map.get(spotify_key, 'Unknown')

def find_mp3_file(track_name, artist_name, duration_ms, folder_path):
    track_clean = str(track_name).lower().strip()
    artist_clean = str(artist_name).lower().strip()
    
    # 1. Both track and artist in filename
    for mp3 in folder_path.rglob('*.mp3'):
        name = mp3.stem.lower()
        if track_clean in name and artist_clean in name:
            return mp3
    
    # 2. Strip leading numbers and try track name only
    for mp3 in folder_path.rglob('*.mp3'):
        name = mp3.stem.lower()
        clean_name = re.sub(r'^[\d\s\.\-_]+', '', name)
        if track_clean in clean_name:
            return mp3
    
    # 3. Fallback: duration match with 5 sec tolerance
    for mp3 in folder_path.rglob('*.mp3'):
        try:
            audio = File(mp3)
            if audio and hasattr(audio.info, 'length'):
                mp3_duration_ms = int(audio.info.length * 1000)
                if abs(mp3_duration_ms - duration_ms) < 5000:
                    return mp3
        except:
            continue
    return None

def write_metadata(mp3_path, row):
    try:
        audio = File(mp3_path)
        if audio is None:
            audio = ID3()

        # Aggressive cleanup
        keys_to_delete = [key for key in audio.keys() if key.startswith('TXXX') or key in ['TBPM', 'TKEY']]
        for key in keys_to_delete:
            del audio[key]

        # Standard tags
        audio['TIT2'] = TIT2(encoding=3, text=str(row.get('Track Name', '')))
        audio['TPE1'] = TPE1(encoding=3, text=str(row.get('Artist Name(s)', '')))
        audio['TALB'] = TALB(encoding=3, text=str(row.get('Album Name', '')))
        audio['TCON'] = TCON(encoding=3, text=str(row.get('Genres', '')))
        audio['TDRC'] = TDRC(encoding=3, text=str(row.get('Release Date', '')))

        # Key & BPM
        camelot = convert_spotify_key_to_camelot(int(row.get('Key', 0)), int(row.get('Mode', 1)))
        audio['TKEY'] = TKEY(encoding=3, text=camelot)
        
        bpm_int = int(round(float(row.get('Tempo', 0))))
        audio['TBPM'] = TBPM(encoding=3, text=str(bpm_int))

        # Optional tags
        audio['TXXX:Danceability'] = TXXX(encoding=3, desc='Danceability', text=str(row.get('Danceability', '')))
        audio['TXXX:Energy'] = TXXX(encoding=3, desc='Energy', text=str(row.get('Energy', '')))

        audio.save(mp3_path, v2_version=3)
        return True, "Success"
    except Exception as e:
        return False, str(e)

# --- MAIN INTERFACE ---
col1, col2 = st.columns(2)
with col1:
    uploaded_csv = st.file_uploader("1. Upload Target Data (.csv)", type=["csv"])
with col2:
    uploaded_zip = st.file_uploader("2. Upload MP3 Batch (.zip)", type=["zip"])

if uploaded_csv is not None and uploaded_zip is not None:
    df = pd.read_csv(uploaded_csv)
    
    with st.expander("Preview CSV Data", expanded=False):
        st.dataframe(df.head(5), use_container_width=True)

    if st.button("🚀 Execute Cloud Tagging Process", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        missing_tracks = []
        success_count = 0
        total_tracks = len(df)

        # Create a secure, temporary directory on the cloud server
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            status_text.text("📦 Unzipping files to temporary secure storage...")
            
            # Extract the uploaded zip into the temp directory
            with zipfile.ZipFile(uploaded_zip, 'r') as zip_ref:
                zip_ref.extractall(tmp_path)
            
            # Process each track in the CSV
            for index, row in df.iterrows():
                track = row.get('Track Name', 'Unknown')
                artist = row.get('Artist Name(s)', 'Unknown')
                duration = int(row.get('Duration (ms)', 0)) if not pd.isna(row.get('Duration (ms)')) else 0
                
                status_text.text(f"🏷️ Tagging ({index + 1}/{total_tracks}): {track} - {artist}")
                
                # Search for the MP3 in the temporary extracted folder
                mp3_path = find_mp3_file(track, artist, duration, tmp_path)
                
                if mp3_path:
                    success, msg = write_metadata(mp3_path, row)
                    if success:
                        success_count += 1
                    else:
                        missing_tracks.append(f"{track} - {artist} (Error: {msg})")
                else:
                    missing_tracks.append(f"{track} - {artist} (Not Found in Zip)")
                
                progress_bar.progress((index + 1) / total_tracks)

            status_text.text("🗜️ Re-zipping tagged files for download...")
            
            # Bundle the newly tagged files back into a zip buffer in memory
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for file_path in tmp_path.rglob("*.mp3"):
                    # Preserve the original structure relative to the temp path
                    arcname = file_path.relative_to(tmp_path)
                    zip_file.write(file_path, arcname=arcname)
            
            status_text.text("✅ Process Complete!")
            
            # Show Summary
            st.success(f"📊 Summary: Successfully tagged {success_count} out of {total_tracks} tracks.")
            if missing_tracks:
                st.warning(f"⚠️ {len(missing_tracks)} tracks were not matched or encountered errors:")
                with st.expander("View Unmatched Tracks"):
                    for t in missing_tracks:
                        st.write(f"- {t}")
            
            # Provide the Download Button
            st.download_button(
                label="📥 Download Tagged MP3s (.zip)",
                data=zip_buffer.getvalue(),
                file_name="Afex_Tagged_Tracks.zip",
                mime="application/zip",
                type="primary"
            )
