import streamlit as st
import pandas as pd
import sys
import os

# Path Fix for accessing auth.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the same bootstrap used in 03_Song_Lister
from afexcloud.layout import bootstrap_page

# --- Spotify availability check ---
try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    SPOTIPY_AVAILABLE = True
except ImportError:
    SPOTIPY_AVAILABLE = False

# Page Configuration
st.set_page_config(
    page_title="ProDJ Smart Playlist Generator", 
    page_icon="🎧", 
    layout="wide"
)

# App Header
st.title("🎧 ProDJ Enterprise Harmonic Flow Engine")
st.markdown("Transform raw client tracklists into seamlessly blended, mathematically optimized event setlists.")

# --- Spotify client authentication (Universal Session Link) ---
from spotipy.cache_handler import CacheHandler
import json

class UniversalCacheHandler(CacheHandler):
    """Bridges the gap between the Main App's memory and local file caches."""
    def get_cached_token(self):
        # 1. Check the Main App's session state memory
        if st.session_state.get("spotify_token_info"):
            return st.session_state["spotify_token_info"]
        
        # 2. Fallback to the default .cache file (used by spotify_auth.py)
        try:
            if os.path.exists(".cache"):
                with open(".cache", "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    def save_token_to_cache(self, token_info):
        st.session_state["spotify_token_info"] = token_info
        try:
            with open(".cache", "w") as f:
                json.dump(token_info, f)
        except Exception:
            pass

def get_spotify_client():
    """Connects to Spotify using whichever token the Main App already secured."""
    if not SPOTIPY_AVAILABLE:
        return None
    
    client_id = st.secrets.get("SPOTIFY_CLIENT_ID")
    client_secret = st.secrets.get("SPOTIFY_CLIENT_SECRET")
    redirect_uri = st.secrets.get("SPOTIFY_REDIRECT_URI", "http://localhost:8501")
    
    if not (client_id and client_secret):
        return {"status": "unauthorized"}

    # Build the auth manager using our custom bridge handler
    sp_oauth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope="playlist-modify-public playlist-modify-private playlist-read-private",
        cache_handler=UniversalCacheHandler(),
        open_browser=False 
    )

    # Ask the auth manager to validate the token using the bridge
    try:
        token_info = sp_oauth.get_cached_token()
    except Exception as e:
        if "invalid_grant" in str(e).lower():
            # 2026 Safeguard: Clear memory if token is older than 6 months
            st.session_state["spotify_token_info"] = None
            if os.path.exists(".cache"):
                os.remove(".cache")
        token_info = None

    if token_info:
        # Authorized! Return a fully built client capable of auto-refreshing
        sp = spotipy.Spotify(auth_manager=sp_oauth)
        return {"status": "authorized", "client": sp}
    else:
        return {"status": "unauthorized"}

# --- CURATOR CONTROLS ---
with st.expander("🎛️ Curator Controls (Click to Adjust Algorithmic Weights)", expanded=True):
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        bpm_weight = st.slider(
            "Tempo (BPM) Strictness", 
            min_value=0.1, max_value=2.0, value=1.60, step=0.05,
            help="Higher values force songs to stay closer in tempo."
        )
    with col_c2:
        harmonic_penalty_val = st.slider(
            "Key Incompatibility Penalty", 
            min_value=1, max_value=20, value=13, step=1,
            help="Higher values heavily penalize non-harmonious key transitions."
        )

    # --- THE NUCLEAR DISCONNECT BUTTON ---
st.sidebar.markdown("---")
st.sidebar.subheader("🛠️ Server Troubleshooting")
if st.sidebar.button("💥 Nuke Spotify Server Cache"):
    # 1. Clear Streamlit's temporary memory
    st.session_state["spotify_token_info"] = None
    if "spotify_oauth_state" in st.session_state:
        del st.session_state["spotify_oauth_state"]
        
    # 2. Hunt down and destroy the physical files on the server disk
    cache_files_destroyed = 0
    for cache_file in [".cache", ".spotify_cache"]:
        if os.path.exists(cache_file):
            try:
                os.remove(cache_file)
                cache_files_destroyed += 1
            except Exception as e:
                st.sidebar.error(f"Failed to delete {cache_file}: {e}")
                
    st.sidebar.success(f"Obliterated {cache_files_destroyed} ghost files! Refresh the page and log in via the Main Dashboard.")

    # --- INITIALIZE SPOTIFY EARLY ---
# Catch the redirect code immediately, outside of any buttons
spotify_status = get_spotify_client()

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

    # 3. AUTOMATIC MAGIC: Calculate Camelot Key and Relative (Alt) Key
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
            bpm_str = f"{int(bpm_weight * 100):03d}"
            penalty_str = str(int(harmonic_penalty_val))
            
            result_df['BPM_Strictness'] = bpm_weight
            result_df['Key_Penalty'] = harmonic_penalty_val
            
            # SAVE TO SESSION STATE SO IT SURVIVES SPOTIFY REDIRECTS
            st.session_state['optimized_df'] = result_df
            st.session_state['dynamic_filename'] = f"{os.path.splitext(uploaded_file.name)[0]}_Optimized_{bpm_str}-{penalty_str}.csv"

        st.success("Setlist successfully generated and stamped!")
        
    # --- DISPLAY RESULTS ONLY IF THEY EXIST IN MEMORY ---
    if 'optimized_df' in st.session_state:
        result_df = st.session_state['optimized_df']
        file_name_dynamic = st.session_state['dynamic_filename']
        
        # --- Display Final Table ---
        st.subheader("✨ Optimized Transition Flow")
        show_cols = [c for c in ['Track URI', 'Track Name', 'Artist Name(s)', 'Tempo', 'Camelot Key', 'Relative Key (Alt)', 'BPM_Strictness', 'Key_Penalty'] if c in result_df.columns]
        st.dataframe(result_df[show_cols], use_container_width=True)
        
        # --- Download CSV ---
        csv_export = result_df[show_cols].to_csv(index=False).encode('utf-8')
        st.download_button(
            label=f"📥 Download Final Client Setlist ({file_name_dynamic})",
            data=csv_export,
            file_name=file_name_dynamic,
            mime="text/csv"
        )
        
        # --- NEW: SPOTIFY UPLOAD SECTION ---
        st.subheader("☁️ Upload to Spotify")
        if not SPOTIPY_AVAILABLE:
            st.warning("⚠️ `spotipy` is not installed. Run `pip install spotipy` to enable Spotify upload.")
        else:
            spotify_playlist_name = st.text_input(
                "Playlist name on Spotify",
                value=file_name_dynamic.replace(".csv", ""),
                help="This name will appear in your Spotify library."
            )
            
            if spotify_status and spotify_status["status"] == "unauthorized":
                st.warning("You must link your Spotify account to upload playlists.")
                # Redirect the user to the central login point
                st.info("👈 **Action Required:** Please navigate to the **Main Dashboard (Home)**, click 'Connect Spotify' in the sidebar, and then return to this page.")
                
            elif spotify_status and spotify_status["status"] == "authorized":
                sp = spotify_status["client"]
                
                if st.button("📤 Create Spotify Playlist", type="secondary"):
                    with st.spinner("Communicating with Spotify..."):
                        try:
                            # Get current user ID
                            user_info = sp.me()
                            user_id = user_info["id"]
                            
                            # Create playlist
                            playlist = sp.user_playlist_create(
                                user=user_id,
                                name=spotify_playlist_name,
                                public=True,
                                description="Generated by ProDJ Harmonic Flow Engine"
                            )
                            playlist_id = playlist["id"]
                            
                            # Extract track IDs from URIs
                            track_ids = []
                            for uri in result_df["Track URI"]:
                                if isinstance(uri, str) and uri.startswith("spotify:track:"):
                                    track_id = uri.split(":")[-1]
                                    track_ids.append(track_id)
                            
                            if not track_ids:
                                st.error("No valid track URIs found. Cannot create playlist.")
                            else:
                                # Add tracks in batches of 100
                                for i in range(0, len(track_ids), 100):
                                    batch = track_ids[i:i+100]
                                    sp.playlist_add_items(playlist_id, batch)
                                
                                playlist_url = playlist["external_urls"]["spotify"]
                                st.success(f"✅ Playlist **{spotify_playlist_name}** created successfully!")
                                st.markdown(f"**[🎵 Open your new playlist in Spotify]({playlist_url})**")
                                
                        except Exception as e:
                            st.error(f"Upload failed: {e}")

else:
    st.info("👆 Upload your raw Spotify CSV file above to begin.")
