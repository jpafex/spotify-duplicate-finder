import streamlit as st
import pandas as pd
import re
import unicodedata
from collections import defaultdict
import sys
import os
from datetime import datetime
import spotipy

# Path Fix for 'pages' folder access
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from afexcloud.layout import bootstrap_page
from spotify_utils import get_playlist_data, get_track_info, process_exportify_csv

# 1. Page Config
st.set_page_config(page_title="Duplicate Finder | AfexCloud", page_icon="🔍", layout="wide")

# 2. Bootstrap Style & Security
auth_manager, token_info = bootstrap_page()

# 3. Tool Helpers
def advanced_normalize(text):
    """Normalization logic to catch subtle duplicates."""
    if not isinstance(text, str): text = str(text)
    text = unicodedata.normalize('NFKD', text)
    text = "".join([c for c in text if not unicodedata.combining(c)])
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return re.sub(r'\s+', ' ', text).strip()

# 4. Tool Logic
st.title("🔍 Duplicate Finder")

# --- NEWBIE GUIDE ---
with st.expander("🆕 New here? How to scan & clean client playlists", expanded=False):
    st.markdown("""
    1.  **Export the client's playlist** as a CSV using [Exportify.net](https://exportify.net/).
    2.  **Upload the CSV** into **Option 1** to identify duplicates.
    3.  **To Delete**: You must own the playlist on your account (use the **Reconstructor** first if needed).
    """)
    st.link_button("🔗 Go to Exportify.net", "https://exportify.net/")

st.write("---")

# Path A: The "Easy Option" (CSV Upload)
st.subheader("📂 Option 1: Upload Exportify CSV")
uploaded_file = st.file_uploader("Drop Exportify CSV here to bypass 2026 Ownership rules", type=["csv"])

if uploaded_file:
    raw_filename = uploaded_file.name.rsplit('.', 1)[0]
    clean_p_name = re.sub(r'[^a-zA-Z0-9_]', '_', raw_filename)
    
    with st.spinner("Scanning for duplicates..."):
        df_csv = process_exportify_csv(uploaded_file)
        
        # Track instances to identify duplicates while keeping the first one
        by_id = defaultdict(list)
        for idx, row in df_csv.iterrows():
            tid = row['Spotify-id']
            if tid and tid != "N/A":
                # We store the 0-based index for the delete logic
                row_dict = row.to_dict()
                row_dict['api_index'] = idx 
                by_id[tid].append(row_dict)
        
        # Identify duplicates (all except the first occurrence of an ID)
        all_dupes = []
        to_delete_items = [] # Used for the Quick Delete action
        
        for tid, instances in by_id.items():
            if len(instances) > 1:
                all_dupes.extend(instances)
                # We queue all instances except the first one for deletion
                for extra in instances[1:]:
                    to_delete_items.append({"uri": tid, "positions": [extra['api_index']]})
        
        if all_dupes:
            df_dupes = pd.DataFrame(all_dupes)
            df_dupes.insert(0, 'Pos', range(1, len(df_dupes) + 1))
            
            if 'BPM' in df_dupes.columns:
                df_dupes['BPM'] = df_dupes['BPM'].astype(str)
            
            st.warning(f"Found {len(all_dupes)} duplicate entries in '{raw_filename}'.")
            st.dataframe(df_dupes.drop(columns=['api_index']), use_container_width=True, hide_index=True)
            
            col1, col2 = st.columns(2)
            with col1:
                # DYNAMIC FILENAME DOWNLOAD
                safe_proj = st.session_state.get("global_proj", "Project")
                timestamp = datetime.now().strftime("%Y%m%d")
                st.download_button(
                    label=f"📥 Download Duplicate Report",
                    data=df_dupes.to_csv(index=False).encode('utf-8'),
                    file_name=f"AfexCloud_{safe_proj}_{clean_p_name}_Duplicates_{timestamp}.csv",
                    mime="text/csv"
                )
            
            with col2:
                # QUICK DELETE BUTTON
                # Requires Spotify Connection and a Playlist ID input
                st.write("---")
                p_url_to_clean = st.text_input("Enter your Mirror Playlist URL to execute deletion:", 
                                              placeholder="Paste the URL of the playlist you OWN")
                
                if st.button("🚨 QUICK DELETE DUPLICATES FROM SPOTIFY"):
                    if not token_info:
                        st.error("Connect Spotify first via the sidebar.")
                    elif not p_url_to_clean:
                        st.error("Provide the URL of the playlist on your account to clean.")
                    else:
                        try:
                            sp = spotipy.Spotify(auth_manager=auth_manager)
                            p_id = p_url_to_clean.split('/')[-1].split('?')[0] if '/' in p_url_to_clean else p_url_to_clean
                            
                            with st.spinner("Deleting duplicates..."):
                                # 2026 COMPLIANCE: The /tracks endpoint is now /items.
                                # We remove specific occurrences by their exact position.
                                # Spotipy's playlist_remove_specific_occurrences_of_items handles this.
                                sp.playlist_remove_specific_occurrences_of_items(p_id, to_delete_items)
                                
                                st.success(f"Successfully removed {len(to_delete_items)} redundant tracks!")
                                st.balloons()
                        except Exception as e:
                            st.error(f"Deletion failed: {e}. (Reminder: You can only delete from playlists you OWN).")
        else:
            st.success(f"No duplicates found in '{raw_filename}'! This playlist is clean.")

st.write("---")

# Path B: The "API Option" (URL Input)
st.subheader("🌐 Option 2: Spotify URL (API Path)")
if not token_info:
    st.warning("Connect Spotify first.")
else:
    sp = spotipy.Spotify(auth_manager=auth_manager)
    url = st.text_input("Enter Playlist URL/ID to scan:")
    if st.button("🚀 Run API Duplicate Scan"):
        # ... (Similar logic to API path in previous tools)
        st.info("Reminder: API scans are subject to the 2026 Ownership Wall.")
