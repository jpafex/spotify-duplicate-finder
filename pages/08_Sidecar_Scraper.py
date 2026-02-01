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

# -----------------------------
# Helpers
# -----------------------------

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


KEY_MAP = {
    0: "C",  1: "C#", 2: "D",  3: "D#", 4: "E",  5: "F",
    6: "F#", 7: "G",  8: "G#", 9: "A", 10: "A#", 11: "B"
}
CAMELOT_MAJOR = {"C":"8B","C#":"3B","D":"10B","D#":"5B","E":"12B","F":"7B","F#":"2B","G":"9B","G#":"4B","A":"11B","A#":"6B","B":"1B"}
CAMELOT_MINOR = {"C":"5A","C#":"12A","D":"7A","D#":"2A","E":"9A","F":"4A","F#":"11A","G":"6A","G#":"1A","A":"8A","A#":"3A","B":"10A"}

def to_camelot(key_name: str | None, mode: int | None) -> str:
    if not key_name or mode is None:
        return "N/A"
    if mode == 1:
        return CAMELOT_MAJOR.get(key_name, "N/A")
    if mode == 0:
        return CAMELOT_MINOR.get(key_name, "N/A")
    return "N/A"


def get_access_token_from_session() -> str | None:
    token_info = st.session_state.get("_spotify_token_info")
    if not token_info or not token_info.get("access_token"):
        return None
    return token_info["access_token"]


def spotify_call(func, *args, max_retries: int = 6, base_sleep: float = 0.8, **kwargs):
    """
    Retry wrapper for Spotify calls:
    - 429: retry-after / backoff
    - 5xx: backoff
    - 401: token expired/invalid -> raise immediately (user must reconnect)
    """
    attempt = 0
    while True:
        try:
            return func(*args, **kwargs)

        except SpotifyException as e:
            attempt += 1
            status = getattr(e, "http_status", None)

            # Token expired/invalid
            if status == 401:
                raise

            if attempt > max_retries:
                raise

            if status == 429:
                retry_after = None
                try:
                    retry_after = int((e.headers or {}).get("Retry-After", "0"))
                except Exception:
                    retry_after = None
                sleep_s = retry_after if (retry_after and retry_after > 0) else (base_sleep * (2 ** (attempt - 1)))
                sleep_s += random.uniform(0, 0.35)
                time.sleep(min(sleep_s, 30))
                continue

            if status in (500, 502, 503, 504):
                sleep_s = base_sleep * (2 ** (attempt - 1)) + random.uniform(0, 0.35)
                time.sleep(min(sleep_s, 20))
                continue

            raise

        except Exception:
            attempt += 1
            if attempt > max_retries:
                raise
            sleep_s = base_sleep * (2 ** (attempt - 1)) + random.uniform(0, 0.35)
            time.sleep(min(sleep_s, 20))


def show_missing_summary(df: pd.DataFrame):
    if df is None or df.empty:
        return

    total = len(df)
    missing_bpm = df["bpm"].isna().sum()
    missing_key = (df["key"] == "N/A").sum()
    missing_both = (df["bpm"].isna() & (df["key"] == "N/A")).sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tracks", f"{total}")
    c2.metric("Missing BPM", f"{missing_bpm} ({missing_bpm/total:.0%})")
    c3.metric("Missing Key", f"{missing_key} ({missing_key/total:.0%})")
    c4.metric("Missing Both", f"{missing_both} ({missing_both/total:.0%})")


@st.cache_data(ttl=1800, show_spinner=False)
def analyze_playlist_cached(playlist_id: str, max_tracks: int, user_cache_key: str) -> tuple[dict, pd.DataFrame]:
    """
    Cached analyzer keyed by:
      - playlist_id
      - max_tracks
      - spotify user id (user_cache_key)

    Token is pulled from session at runtime (so we don't destroy caching each time token rotates).
    """
    access_token = get_access_token_from_session()
    if not access_token:
        # If cached call runs without token, just return empty;
        # UI will prompt connect/reconnect.
        return {}, pd.DataFrame()

    sp = spotipy.Spotify(auth=access_token)

    pl = spotify_call(sp.playlist, playlist_id, fields="name,owner(display_name),tracks.total")
    total = pl["tracks"]["total"]
    target_total = total if (max_tracks <= 0) else min(total, max_tracks)

    # Fetch tracks
    items = []
    offset = 0
    limit = 100

    while offset < target_total:
        batch = spotify_call(
            sp.playlist_items,
            playlist_id,
            limit=min(limit, target_total - offset),
            offset=offset,
            fields="items(track(id,name,artists(name),album(name),duration_ms,popularity,explicit)),next,total",
        )

        for it in batch.get("items", []):
            tr = it.get("track")
            if not tr or not tr.get("id"):
                continue

            artists = ", ".join([a["name"] for a in tr.get("artists", []) if a.get("name")])
            items.append({
                "position": len(items) + 1,
                "track_id": tr["id"],
                "track_name": tr.get("name", ""),
                "artists": artists,
                "album": (tr.get("album") or {}).get("name", ""),
                "duration_ms": tr.get("duration_ms", 0),
                "popularity": tr.get("popularity", None),
                "explicit": bool(tr.get("explicit", False)),
            })

        offset = len(items)
        if not batch.get("next"):
            break

    if not items:
        return pl, pd.DataFrame()

    track_ids = [t["track_id"] for t in items]

    feats_by_id = {}
    for i in range(0, len(track_ids), 100):
        chunk = track_ids[i:i + 100]
        feats = spotify_call(sp.audio_features, chunk)
        for tid, f in zip(chunk, feats):
            feats_by_id[tid] = f

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

    return pl, pd.DataFrame(rows)


# -----------------------------
# UI
# -----------------------------

st.title("🕵️ Sidecar Musical Analyzer (Spotify Audio Features)")
st.info("Uses Spotify Audio Features to return real BPM + Key (not scraping).")

access_token = get_access_token_from_session()
if access_token is None:
    st.warning("Connect Spotify first using the sidebar button.")
    st.stop()

# Create a client to get user id (for safe multi-user caching)
sp = spotipy.Spotify(auth=access_token)
try:
    me = spotify_call(sp.current_user)
    user_cache_key = me.get("id", "unknown_user")
except SpotifyException as e:
    if getattr(e, "http_status", None) == 401:
        st.error("Your Spotify session expired. Please click **Disconnect Spotify** then **Connect Spotify** in the sidebar.")
        st.stop()
    raise

option = st.radio(
    "Options (beta)",
    ["1) Analyze playlist by URL/ID", "2) Run example test playlist", "3) About / Help"],
    index=0
)

def run_analysis(playlist_input: str, max_tracks: int):
    playlist_id = extract_playlist_id(playlist_input)
    if not playlist_id:
        st.error("Invalid playlist URL or ID.")
        return

    with st.spinner("Analyzing playlist (cached + rate-limit safe)…"):
        try:
            pl_info, df = analyze_playlist_cached(playlist_id, int(max_tracks), user_cache_key)
        except SpotifyException as e:
            status = getattr(e, "http_status", None)
            if status == 401:
                st.error("Spotify token expired while analyzing. Please **Disconnect Spotify** then **Connect Spotify** in the sidebar, then retry.")
                return
            st.error("Spotify returned an error while fetching audio features.")
            st.caption(f"HTTP status: {status}")
            return

    if df is None or df.empty:
        st.warning("No playable tracks found (or access denied).")
        return

    pl_name = (pl_info or {}).get("name", "Playlist")
    owner = ((pl_info or {}).get("owner") or {}).get("display_name", "")
    st.subheader(f"🎵 {pl_name} — {owner}".strip(" —"))

    show_missing_summary(df)

    st.dataframe(df, use_container_width=True, hide_index=True)

    safe_proj = st.session_state.get("_safe_proj", "project")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"{safe_proj}_Sidecar_Analyzer_{stamp}.csv"

    st.download_button(
        "📥 Download CSV",
        df.to_csv(index=False).encode("utf-8"),
        out_name,
        "text/csv",
    )

    with st.expander("⚙️ Cache controls"):
        st.caption("If you update a playlist and want fresh results immediately, clear the cache.")
        if st.button("Clear Sidecar cache now"):
            st.cache_data.clear()
            st.success("Cache cleared. Re-run analysis.")


if option.startswith("1"):
    playlist_input = st.text_input("Enter Spotify Playlist URL or ID:")
    max_tracks = st.number_input("Max tracks (0 = ALL)", min_value=0, value=0, step=10)

    if st.button("🚀 Analyze Playlist"):
        run_analysis(playlist_input, int(max_tracks))

elif option.startswith("2"):
    test_url = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
    st.write("Example playlist URL:")
    playlist_input = st.text_input("Test playlist URL/ID", value=test_url)
    max_tracks = st.number_input("Max tracks (0 = ALL)", min_value=0, value=15, step=5)

    if st.button("🧪 Run Test"):
        run_analysis(playlist_input, int(max_tracks))

else:
    st.markdown(
        """
**What this does**
- Pulls playlist tracks with Spotify API
- Fetches **Audio Features** for each track
- Returns **BPM (tempo)** + **Key** + **Mode** + **Camelot**

**Upgrades included**
- Missing BPM/Key stats (percent + counts)
- Rate-limit safe retry/backoff (handles 429 + transient 5xx)
- Caching keyed by (playlist, max_tracks, user_id) so reruns are instant

**Notes**
- Some tracks may show `N/A` if Spotify has no audio features (local/unavailable tracks).
        """
    )
