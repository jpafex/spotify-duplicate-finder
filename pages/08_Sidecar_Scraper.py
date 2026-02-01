import re
import time
import random
from datetime import datetime
import pandas as pd
import streamlit as st
import spotipy
from spotipy.exceptions import SpotifyException
from afexcloud.layout import bootstrap_page

bootstrap_page()

# Bump this any time you change logic to automatically bust Streamlit cache keys.
SIDECAR_CODE_VERSION = "1.0.1"  # Updated version for cache busting

KEY_MAP = {
    0: "C",  1: "C#", 2: "D",  3: "D#", 4: "E",  5: "F",
    6: "F#", 7: "G",  8: "G#", 9: "A", 10: "A#", 11: "B"
}
CAMELOT_MAJOR = {"C":"8B","C#":"3B","D":"10B","D#":"5B","E":"12B","F":"7B","F#":"2B","G":"9B","G#":"4B","A":"11B","A#":"6B","B":"1B"}
CAMELOT_MINOR = {"C":"5A","C#":"12A","D":"7A","D#":"2A","E":"9A","F":"4A","F#":"11A","G":"6A","G#":"1A","A":"8A","A#":"3A","B":"10A"}

CACHE_TTL_SECONDS = 1800  # 30 min


def extract_playlist_id(playlist_input: str) -> str | None:
    if not playlist_input:
        return None
    playlist_input = playlist_input.strip()
    m = re.search(r"open\.spotify\.com/playlist/([a-zA-Z0-9]+)", playlist_input)
    if m:
        return m.group(1)
    if len(playlist_input) == 22 and playlist_input.isalnum():
        return playlist_input
    return None


def to_camelot(key_name: str | None, mode: int | None) -> str:
    if not key_name or mode is None:
        return "N/A"
    if mode == 1:
        return CAMELOT_MAJOR.get(key_name, "N/A")
    if mode == 0:
        return CAMELOT_MINOR.get(key_name, "N/A")
    return "N/A"


def get_access_token_from_session() -> str | None:
    """Get Spotify access token with enhanced debugging for web deployment"""
    # Try multiple possible session state keys
    possible_keys = ["_spotify_token_info", "token_info", "spotify_token"]
    
    for key in possible_keys:
        if key in st.session_state:
            token_info = st.session_state[key]
            st.info(f"Found token in key: {key}")
            
            # Handle different token formats
            if isinstance(token_info, dict) and "access_token" in token_info:
                token = token_info.get("access_token")
                if token:
                    # Quick validation of token format
                    if len(token) > 30:  # Basic validation
                        return token
                    else:
                        st.warning(f"Token too short: {len(token)} chars")
            elif isinstance(token_info, str):
                if len(token_info) > 30:
                    return token_info
    
    st.warning("No valid token found in session state")
    return None


def spotify_call(func, *args, max_retries: int = 7, base_sleep: float = 0.8, **kwargs):
    """Enhanced with better debugging"""
    attempt = 0
    while True:
        try:
            return func(*args, **kwargs)

        except SpotifyException as e:
            attempt += 1
            status = getattr(e, "http_status", None)
            
            # Log the error for debugging
            st.write(f"SpotifyException: Status {status}, Attempt {attempt}/{max_retries}")
            
            if status == 401:
                st.error("401 Unauthorized - Token may have expired")
                raise

            if attempt > max_retries:
                st.error(f"Max retries ({max_retries}) exceeded")
                raise

            if status == 429:
                retry_after = None
                try:
                    retry_after = int((e.headers or {}).get("Retry-After", "0"))
                except Exception:
                    retry_after = None
                sleep_s = retry_after if (retry_after and retry_after > 0) else (base_sleep * (2 ** (attempt - 1)))
                sleep_s += random.uniform(0, 0.35)
                st.warning(f"Rate limited. Sleeping for {sleep_s:.1f} seconds...")
                time.sleep(min(sleep_s, 30))
                continue

            if status in (500, 502, 503, 504):
                sleep_s = base_sleep * (2 ** (attempt - 1)) + random.uniform(0, 0.35)
                st.warning(f"Server error {status}. Sleeping for {sleep_s:.1f} seconds...")
                time.sleep(min(sleep_s, 20))
                continue

            st.error(f"Unhandled Spotify error: {e}")
            raise

        except Exception as e:
            attempt += 1
            st.error(f"General error: {type(e).__name__}: {str(e)}")
            if attempt > max_retries:
                raise
            sleep_s = base_sleep * (2 ** (attempt - 1)) + random.uniform(0, 0.35)
            time.sleep(min(sleep_s, 20))


def fetch_audio_features_safe(sp: spotipy.Spotify, track_ids: list[str]) -> dict[str, dict | None]:
    """Fetch audio features with enhanced error handling"""
    feats_by_id: dict[str, dict | None] = {}
    
    if not track_ids:
        return feats_by_id

    def helper(chunk: list[str]):
        if not chunk:
            return
        try:
            st.write(f"Fetching audio features for {len(chunk)} tracks...")
            feats = spotify_call(sp.audio_features, chunk)
            
            if feats is None:
                st.warning(f"No audio features returned for chunk of {len(chunk)} tracks")
                for tid in chunk:
                    feats_by_id[tid] = None
                return
                
            for tid, f in zip(chunk, feats):
                feats_by_id[tid] = f
                
        except SpotifyException as e:
            status = getattr(e, "http_status", None)
            st.write(f"Audio features error: Status {status}")
            
            if status in (400, 403) and len(chunk) > 1:
                mid = len(chunk) // 2
                st.write(f"Splitting chunk of {len(chunk)} into {mid} and {len(chunk)-mid}")
                helper(chunk[:mid])
                helper(chunk[mid:])
                return
                
            for tid in chunk:
                feats_by_id[tid] = None

    # Process in smaller batches for reliability
    batch_size = 50  # Reduced from 100 for more reliability
    for i in range(0, len(track_ids), batch_size):
        chunk = track_ids[i:i + batch_size]
        st.write(f"Processing batch {i//batch_size + 1}/{(len(track_ids)-1)//batch_size + 1}")
        helper(chunk)

    return feats_by_id


def show_missing_summary(df: pd.DataFrame):
    if df is None or df.empty:
        st.info("No data to summarize")
        return
    total = len(df)
    missing_bpm = df["bpm"].isna().sum()
    missing_key = (df["key"] == "N/A").sum()
    missing_both = (df["bpm"].isna() & (df["key"] == "N/A")).sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tracks", f"{total}")
    if total > 0:
        c2.metric("Missing BPM", f"{missing_bpm} ({missing_bpm/total:.0%})")
        c3.metric("Missing Key", f"{missing_key} ({missing_key/total:.0%})")
        c4.metric("Missing Both", f"{missing_both} ({missing_both/total:.0%})")
    else:
        c2.metric("Missing BPM", "0")
        c3.metric("Missing Key", "0")
        c4.metric("Missing Both", "0")


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def analyze_playlist_cached(
    playlist_id: str,
    max_tracks: int,
    user_cache_key: str,
    access_token: str,
    code_version: str,
) -> tuple[dict, pd.DataFrame, dict]:
    """
    Returns: (playlist_info, dataframe, diagnostics)
    """
    st.write(f"Starting analysis for playlist: {playlist_id}")
    st.write(f"Access token length: {len(access_token) if access_token else 0}")
    
    try:
        sp = spotipy.Spotify(auth=access_token)
        
        # Test the token with a simple call
        try:
            test_user = spotify_call(sp.current_user)
            st.write(f"Authenticated as: {test_user.get('display_name', 'Unknown')}")
        except Exception as e:
            st.error(f"Token validation failed: {e}")
            return {}, pd.DataFrame(), {"error": "Token validation failed"}

        # Get playlist info
        pl = spotify_call(
            sp.playlist, 
            playlist_id, 
            fields="name,owner(display_name),tracks.total,public"
        )
        
        total = pl.get("tracks", {}).get("total", 0)
        target_total = total if max_tracks <= 0 else min(total, max_tracks)
        
        st.write(f"Playlist: {pl.get('name')}, Total tracks: {total}, Target: {target_total}")

        diagnostics = {
            "playlist_total_tracks": total,
            "target_total_tracks": target_total,
            "raw_items_seen": 0,
            "skipped_missing_track": 0,
            "skipped_missing_id": 0,
            "skipped_local": 0,
            "skipped_non_track_type": 0,
            "kept_tracks": 0,
            "playlist_name": pl.get("name", "Unknown"),
            "is_public": pl.get("public", False)
        }

        items = []
        offset = 0
        limit = 50  # Reduced for reliability

        while offset < target_total and len(items) < target_total:
            batch_limit = min(limit, target_total - offset)
            st.write(f"Fetching batch: offset={offset}, limit={batch_limit}")
            
            try:
                batch = spotify_call(
                    sp.playlist_items,
                    playlist_id,
                    limit=batch_limit,
                    offset=offset,
                    fields="items(track(id,type,is_local,name,artists(name),album(name),duration_ms,popularity,explicit)),next,total",
                )
            except Exception as e:
                st.error(f"Failed to fetch playlist items: {e}")
                break

            if not batch or "items" not in batch:
                st.warning("No items returned from API")
                break

            for it in batch.get("items", []):
                diagnostics["raw_items_seen"] += 1

                tr = it.get("track")
                if not tr:
                    diagnostics["skipped_missing_track"] += 1
                    continue

                tid = tr.get("id")
                if not tid:
                    diagnostics["skipped_missing_id"] += 1
                    continue

                # Tolerant defaults
                ttype = tr.get("type", "track")
                is_local = bool(tr.get("is_local", False))

                if ttype != "track":
                    diagnostics["skipped_non_track_type"] += 1
                    continue
                if is_local:
                    diagnostics["skipped_local"] += 1
                    continue

                artists_list = tr.get("artists", [])
                artists = ", ".join([a["name"] for a in artists_list if a.get("name")])

                items.append({
                    "position": len(items) + 1,
                    "track_id": tid,
                    "track_name": tr.get("name", ""),
                    "artists": artists,
                    "album": (tr.get("album") or {}).get("name", ""),
                    "duration_ms": tr.get("duration_ms", 0),
                    "popularity": tr.get("popularity", None),
                    "explicit": bool(tr.get("explicit", False)),
                })

            offset += len(batch.get("items", []))
            diagnostics["kept_tracks"] = len(items)
            
            if not batch.get("next"):
                break
                
            if len(items) >= target_total:
                break

        st.write(f"Collected {len(items)} track items")

        if not items:
            st.warning("No tracks collected from playlist")
            return pl, pd.DataFrame(), diagnostics

        # Get audio features
        track_ids = [t["track_id"] for t in items]
        st.write(f"Fetching audio features for {len(track_ids)} tracks...")
        
        feats_by_id = fetch_audio_features_safe(sp, track_ids)
        
        # Count successful feature fetches
        successful_feats = sum(1 for f in feats_by_id.values() if f is not None)
        st.write(f"Successfully fetched audio features for {successful_feats}/{len(track_ids)} tracks")
        
        # Build results
        rows = []
        for t in items:
            f = feats_by_id.get(t["track_id"]) or {}
            
            tempo = f.get("tempo", None)
            key_int = f.get("key", None)
            mode = f.get("mode", None)

            key_name = KEY_MAP.get(key_int) if isinstance(key_int, int) and key_int >= 0 else None
            camelot = to_camelot(key_name, mode)

            rows.append({
                "track_position": t["position"],
                "track_name": t["track_name"],
                "artists": t["artists"],
                "album": t["album"],
                "bpm": round(tempo, 2) if isinstance(tempo, (int, float)) else None,
                "key": key_name or "N/A",
                "mode": "major" if mode == 1 else ("minor" if mode == 0 else "N/A"),
                "camelot": camelot,
                "danceability": f.get("danceability", None),
                "energy": f.get("energy", None),
                "valence": f.get("valence", None),
                "duration_min": round((t["duration_ms"] or 0) / 60000, 2),
                "popularity": t["popularity"],
                "explicit": "Yes" if t["explicit"] else "No",
                "track_id": t["track_id"],
            })

        df = pd.DataFrame(rows)
        st.write(f"Created dataframe with {len(df)} rows")
        return pl, df, diagnostics
        
    except Exception as e:
        st.error(f"Analysis failed: {type(e).__name__}: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return {}, pd.DataFrame(), {"error": str(e)}


# -----------------------------
# UI
# -----------------------------

st.title("🕵️ Sidecar Musical Analyzer (Spotify Audio Features)")
st.caption("BPM + Key + Camelot from Spotify Audio Features. Includes rate-limit safety + caching + diagnostics.")

# Debug info
with st.expander("🔧 Debug Information", expanded=False):
    st.write("Session State Keys:", list(st.session_state.keys()))
    if "_spotify_token_info" in st.session_state:
        token_info = st.session_state["_spotify_token_info"]
        if isinstance(token_info, dict):
            st.write("Token Info Keys:", list(token_info.keys()))
            if "access_token" in token_info:
                token = token_info["access_token"]
                st.write(f"Token length: {len(token)}")
                st.write(f"Token preview: {token[:20]}...")

# Cache control
with st.expander("⚙️ Cache controls", expanded=False):
    st.caption("If you previously tested a broken Sidecar version, clear cache to remove stale empty results.")
    if st.button("Clear Sidecar cache now"):
        st.cache_data.clear()
        st.success("Cache cleared. Run analysis again.")

# Get access token
access_token = get_access_token_from_session()
if access_token is None:
    st.warning("""
    **No Spotify token found.** 
    
    Please:
    1. Go to the main page
    2. Click **Connect Spotify** in the sidebar
    3. Authorize the app
    4. Return to this page
    """)
    st.stop()

# Get user info for cache key
try:
    sp_me = spotipy.Spotify(auth=access_token)
    me = spotify_call(sp_me.current_user)
    user_id = me.get("id", "unknown_user")
    user_display = me.get("display_name", "Unknown")
    st.sidebar.info(f"Logged in as: {user_display}")
    user_cache_key = f"{user_id}_{SIDECAR_CODE_VERSION}"
except SpotifyException as e:
    if getattr(e, "http_status", None) == 401:
        st.error("""
        **Spotify session expired.**
        
        Please:
        1. Click **Disconnect Spotify** in the sidebar
        2. Click **Connect Spotify** again
        3. Re-authorize the app
        """)
        st.stop()
    st.error(f"Failed to get user info: {e}")
    user_cache_key = "error_user"

option = st.radio(
    "Options",
    ["1) Analyze playlist by URL/ID", "2) Run example test playlist", "3) About / Help"],
    index=0
)


def run_analysis(playlist_input: str, max_tracks: int):
    playlist_id = extract_playlist_id(playlist_input)
    if not playlist_id:
        st.error("Invalid playlist URL or ID.")
        st.info("Example format: https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M")
        return

    st.write(f"Analyzing playlist ID: {playlist_id}")
    
    with st.spinner("Analyzing playlist (this may take a minute)..."):
        try:
            pl_info, df, diag = analyze_playlist_cached(
                playlist_id=playlist_id,
                max_tracks=int(max_tracks),
                user_cache_key=user_cache_key,
                access_token=access_token,
                code_version=SIDECAR_CODE_VERSION,
            )
        except SpotifyException as e:
            status = getattr(e, "http_status", None)
            if status == 401:
                st.error("""
                **Spotify token expired.**
                
                Please:
                1. Click **Disconnect Spotify** in the sidebar
                2. Click **Connect Spotify** again
                3. Re-authorize the app
                """)
                return
            st.error(f"Spotify returned an error: {e}")
            return
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            return

    if not pl_info:
        st.error("Failed to get playlist information")
        return

    pl_name = pl_info.get("name", "Playlist")
    owner = (pl_info.get("owner") or {}).get("display_name", "")
    st.subheader(f"🎵 {pl_name}")
    if owner:
        st.caption(f"Created by: {owner}")

    # Diagnostics
    with st.expander("🔎 Diagnostics", expanded=True):
        st.json(diag)
        
        if "error" in diag:
            st.error(f"Error during analysis: {diag['error']}")
        elif diag.get("kept_tracks", 0) == 0:
            st.warning("No tracks were processed. Possible reasons:")
            st.markdown("""
            - Playlist is empty
            - All tracks are local files (not available on Spotify)
            - You don't have permission to access this playlist
            - Playlist is private and you're not a collaborator
            """)

    if df is None or df.empty:
        if diag.get("kept_tracks", 0) > 0:
            st.warning("Tracks were found but no audio features were retrieved.")
        else:
            st.warning("No playable Spotify tracks were found.")
        return

    # Show summary
    show_missing_summary(df)
    
    # Show data
    st.dataframe(
        df, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "track_position": st.column_config.NumberColumn("Position", width="small"),
            "track_name": st.column_config.TextColumn("Track", width="large"),
            "artists": st.column_config.TextColumn("Artists", width="medium"),
            "bpm": st.column_config.NumberColumn("BPM", width="small"),
            "key": st.column_config.TextColumn("Key", width="small"),
            "camelot": st.column_config.TextColumn("Camelot", width="small"),
            "duration_min": st.column_config.NumberColumn("Duration", format="%.2f", width="small"),
        }
    )

    # Download button
    safe_proj = st.session_state.get("_safe_proj", "project")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"{safe_proj}_Sidecar_Analyzer_{stamp}.csv"

    st.download_button(
        "📥 Download CSV",
        df.to_csv(index=False).encode("utf-8"),
        out_name,
        "text/csv",
    )


if option.startswith("1"):
    st.markdown("### Analyze Your Playlist")
    playlist_input = st.text_input(
        "Enter Spotify Playlist URL or ID:", 
        value="",
        placeholder="https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
    )
    max_tracks = st.number_input(
        "Max tracks to analyze (0 = ALL)", 
        min_value=0, 
        value=50, 
        step=10,
        help="Start with a smaller number for testing"
    )

    if st.button("🚀 Analyze Playlist", type="primary"):
        run_analysis(playlist_input, int(max_tracks))

elif option.startswith("2"):
    st.markdown("### Test with Example Playlist")
    test_url = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
    st.write("This is a public playlist for testing:")
    st.code(test_url)
    
    playlist_input = st.text_input("Test playlist URL/ID", value=test_url)
    max_tracks = st.number_input("Max tracks to analyze", min_value=1, value=20, step=5)

    if st.button("🧪 Run Test", type="secondary"):
        run_analysis(playlist_input, int(max_tracks))

else:
    st.markdown(
        """
        ## About / Help
        
        **What this tool does:**
        - Reads playlist tracks via Spotify API
        - Retrieves **Audio Features** (BPM, Key, Energy, Danceability, etc.)
        - Converts keys to Camelot notation for DJs
        - Exports results as CSV
        
        **Common Issues & Solutions:**
        
        1. **"No results" or empty BPM/Key columns:**
           - Try **Clear Sidecar cache** button
           - Ensure playlist is public or you have access
           - Start with the test playlist to verify functionality
        
        2. **Authentication errors:**
           - Use **Disconnect Spotify** then **Connect Spotify** in sidebar
           - Make sure you've authorized all required scopes
        
        3. **Rate limiting:**
           - The app automatically handles rate limits with exponential backoff
           - Try analyzing fewer tracks (50-100 at a time)
        
        **Tips for best results:**
        - Start with 50 tracks for testing
        - Use public playlists initially
        - Check the Diagnostics panel for detailed information
        
        **Version:** 1.0.1
        **Last Updated:** Enhanced for web deployment
        """
    )
