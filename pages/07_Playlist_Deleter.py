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
st.info("Review, copy, or download your playlist data before performing batch deletions.")

if not token_info:
    st.warning("Connect Spotify first via the sidebar to access your library.")
else:
    sp = spotipy.Spotify(auth_manager=auth_manager)

    # Button to fetch fresh data from Spotify
    if st.button("🔍 Load My Playlists"):
        with st.spinner("Fetching library..."):
            results = sp.current_user_playlists(limit=50)
            playlists = []
            for p in results['items']:
                playlists.append({
                    "Delete?": False,
                    "Playlist Name": p['name'],
                    "Spotify ID": p['id'],
                    "Tracks": p['tracks']['total'],
                    "Owner": p['owner']['display_name']
                })
            st.session_state["deleter_table"] = pd.DataFrame(playlists)

    # If data is loaded, show the interactive tools
    if "deleter_table" in st.session_state and not st.session_state["deleter_table"].empty:
        df = st.session_state["deleter_table"]

        st.write("---")
        st.subheader("📋 Step 1: Pre-Deletion Inventory")
        st.write("Use this table to copy specific IDs or segments. You can also download the full list for your records.")

        # The "Table of Sorts": Allows highlighting, copying, and sorting
        # We use data_editor to allow the "Delete?" checkbox column
        edited_df = st.data_editor(
            df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Delete?": st.column_config.CheckboxColumn(help="Select to queue for deletion"),
                "Spotify ID": st.column_config.TextColumn(help="Copy this ID for your logs"),
                "Tracks": st.column_config.NumberColumn(format="%d")
            },
            disabled=["Playlist Name", "Spotify ID", "Tracks", "Owner"] # Prevent accidental edits
        )

        # Pre-Deletion Download
        csv_inventory = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Current Inventory (CSV)",
            data=csv_inventory,
            file_name=f"Pre_Deletion_Inventory_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            help="Save this list before you delete anything."
        )

        st.write("---")
        st.subheader("🔥 Step 2: Batch Deletion")
        
        # Filter for rows where the user checked "Delete?"
        to_del_df = edited_df[edited_df["Delete?"] == True]
        
        if not to_del_df.empty:
            st.warning(f"You have selected {len(to_del_df)} playlists for deletion.")
            
            if st.button("🚨 CONFIRM & DELETE SELECTED"):
                success_count = 0
                log_entries = []
                
                for _, row in to_del_df.iterrows():
                    try:
                        sp.current_user_unfollow_playlist(row["Spotify ID"])
                        log_entries.append({
                            "Status": "Deleted",
                            "Name": row["Playlist Name"],
                            "ID": row["Spotify ID"],
                            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        success_count += 1
                    except Exception as e:
                        st.error(f"Error deleting {row['Playlist Name']}: {e}")

                st.success(f"Successfully removed {success_count} playlists from your library.")
                
                # Deletion Proof / Validation Log
                proof_df = pd.DataFrame(log_entries)
                st.download_button(
                    label="📜 Download Deletion Proof (Log)",
                    data=proof_df.to_csv(index=False).encode('utf-8'),
                    file_name=f"Deletion_Proof_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
                
                # Clear state to force a refresh on next load
                del st.session_state["deleter_table"]
        else:
            st.info("Select playlists in the table above to enable the delete button.")
