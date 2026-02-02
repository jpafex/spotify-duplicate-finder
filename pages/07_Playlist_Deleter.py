import streamlit as st
import pandas as pd
import spotipy
from datetime import datetime
from afexcloud.layout import bootstrap_page
from afexcloud.spotify_auth import get_auth_manager, get_valid_token_info

# 1. Page Config
st.set_page_config(page_title="Playlist Deleter | AfexCloud", page_icon="🗑️", layout="wide")

# 2. Bootstrap Style & Security
auth_manager, token_info = bootstrap_page()

# 3. Tool Logic
st.title("🗑️ Playlist Deleter")
st.info("Your Playlist IDs are now automatically formatted as 'Spotify URIs' for easier pasting into DJ software.")

if not token_info:
    st.warning("Connect Spotify first via the sidebar to access your library.")
else:
    sp = spotipy.Spotify(auth_manager=auth_manager)

    # Button to fetch fresh data
    if st.button("🔍 Load My Playlists"):
        with st.spinner("Fetching library..."):
            results = sp.current_user_playlists(limit=50)
            playlists = []
            for p in results['items']:
                # AUTOMATIC URI CONVERSION: We add the prefix here as requested
                full_uri = f"spotify:playlist:{p['id']}"
                
                playlists.append({
                    "Delete?": False,
                    "Playlist Name": p['name'],
                    "Spotify URI": full_uri,
                    "Tracks": p['tracks']['total'],
                    "Owner": p['owner']['display_name']
                })
            st.session_state["deleter_table"] = pd.DataFrame(playlists)

    # Display Interactive Table
    if "deleter_table" in st.session_state and not st.session_state["deleter_table"].empty:
        df = st.session_state["deleter_table"]

        st.write("---")
        st.subheader("📋 Step 1: Pre-Deletion Inventory")
        st.caption("Tip: You can highlight and copy (Ctrl+C) any URI directly from this table.")

        # Interactive Table for copying and selecting
        edited_df = st.data_editor(
            df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Delete?": st.column_config.CheckboxColumn(help="Queue for deletion"),
                "Spotify URI": st.column_config.TextColumn(help="Ready-to-use URI for DJ software"),
            },
            disabled=["Playlist Name", "Spotify URI", "Tracks", "Owner"]
        )

        # Pre-Deletion Download
        csv_inventory = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Current Inventory (CSV)",
            data=csv_inventory,
            file_name=f"Playlist_Inventory_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

        st.write("---")
        st.subheader("🔥 Step 2: Batch Deletion")
        
        to_del_df = edited_df[edited_df["Delete?"] == True]
        
        if not to_del_df.empty:
            st.warning(f"You have selected {len(to_del_df)} playlists for deletion.")
            
            if st.button("🚨 CONFIRM & DELETE SELECTED"):
                success_count = 0
                log_entries = []
                
                for _, row in to_del_df.iterrows():
                    try:
                        # Extract the raw ID back out for the API call
                        raw_id = row["Spotify URI"].split(":")[-1]
                        sp.current_user_unfollow_playlist(raw_id)
                        
                        log_entries.append({
                            "Status": "Deleted",
                            "Name": row["Playlist Name"],
                            "URI": row["Spotify URI"],
                            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        success_count += 1
                    except Exception as e:
                        st.error(f"Error: {e}")

                st.success(f"Successfully removed {success_count} playlists.")
                
                # Deletion Proof Download
                proof_df = pd.DataFrame(log_entries)
                st.download_button(
                    label="📜 Download Deletion Proof (Log)",
                    data=proof_df.to_csv(index=False).encode('utf-8'),
                    file_name=f"Deletion_Log_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
                
                # Clear state to refresh on next load
                del st.session_state["deleter_table"]
        else:
            st.info("Check the 'Delete?' boxes above to begin.")
