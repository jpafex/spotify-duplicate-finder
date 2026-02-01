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
SIDECAR_CODE_VERSION = "1.0.0"

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
    token_info = st.session_state.get("_spotify_token_info")
    if not token_info or not token_info.get("access_token"):
        return None
    return token_info["access_token"]


def spotify_call(func, *args, max_retries: int = 7, base_sleep: float = 0.8, **kwargs):
    attempt = 0
    while True:
        try:
            return func(*args, **kwargs)

        except SpotifyException as e:
            attempt += 1
            status = getattr(e, "http_status", None)

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


def fetch_audio_features_safe(sp: spotipy.Spotify, track_ids: list[str]) -> dict[str, dict | None]:
    feats_by_id: dict[str, dict | None] = {}

    def helper(chunk: list[str]):
        if not chunk:
            return
        try:
            feats = spotify_call(sp.audio_features, chunk)
            for tid, f in zip(chunk, feats):
                feats_by_id[tid] = f
        except SpotifyException as e:
            status = getattr(e, "http_status", None)
            if status in (400, 403) and len(chunk) > 1:
                mid = len(chunk) // 2
                helper(chunk[:mid])
                helper(chunk[mid:])
                return
            for tid in chunk:
                feats_by_id[tid] = None

    for i in range(0, len(track_ids), 100):
        helper(track_ids[i:i + 100])

    return feats_by_id


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
    diagnostics helps explain "no results".
    """
    sp = spotipy.Spotify(auth=access_token)

    pl = spotify_call(sp.playlist, playlist_id, fields="name,owner(display_name),tracks.total")
    total = pl["tracks"]["total"]
    target_total = total if max_tracks <= 0 else min(total, max_tracks)

    diagnostics = {
        "playlist_total_tracks": total,
        "target_total_tracks": target_total,
        "raw_items_seen": 0,
        "skipped_missing_track": 0,
        "skipped_missing_id": 0,
        "skipped_local": 0,
        "skipped_non_track_type": 0,
        "kept_tracks": 0,
    }

    items = []
    offset = 0
    limit = 100

    while offset < target_total:
        batch = spotify_call(
            sp.playlist_items,
            playlist_id,
            limit=min(limit, target_total - offset),
            offset=offset,
            # include type + is_local, but we will be tolerant if they are missing
            fields="items(track(id,type,is_local,name,artists(name),album(name),duration_ms,popularity,explicit)),next,total",
        )

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

            # Tolerant defaults (IMPORTANT)
            ttype = tr.get("type", "track")         # if missing, assume track
            is_local = bool(tr.get("is_local", False))  # if missing, assume not local

            if ttype != "track":
                diagnostics["skipped_non_track_type"] += 1
                continue
            if is_local:
                diagnostics["skipped_local"] += 1
                continue

            artists = ", ".join([a["name"] for a in tr.get("artists", []) if a.get("name")])

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

        offset = len(items)
        if not batch.get("next"):
            break

    diagnostics["kept_tracks"] = len(items)

    if not items:
        return pl, pd.DataFrame(), diagnostics

    track_ids = [t["track_id"] for t in items]
    feats_by_id = fetch_audio_features_safe(sp, track_ids)

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
    return pl, df, diagnostics


# -----------------------------
# UI
# -----------------------------

st.title("🕵️ Sidecar Musical Analyzer (Spotify Audio Features)")
st.caption("BPM + Key + Camelot from Spotify Audio Features. Includes rate-limit safety + caching + diagnostics.")

# Cache control ALWAYS visible (even when results empty)
with st.expander("⚙️ Cache controls", expanded=False):
    st.caption("If you previously tested a broken Sidecar version, clear cache to remove stale empty results.")
    if st.button("Clear Sidecar cache now"):
        st.cache_data.clear()
        st.success("Cache cleared. Run analysis again.")

access_token = get_access_token_from_session()
if access_token is None:
    st.warning("Connect Spotify first using the sidebar button.")
    st.stop()

# Get Spotify user id (for multi-user cache separation)
sp_me = spotipy.Spotify(auth=access_token)
try:
    me = spotify_call(sp_me.current_user)
    user_cache_key = me.get("id", "unknown_user")
except SpotifyException as e:
    if getattr(e, "http_status", None) == 401:
        st.error("Your Spotify session expired. Please **Disconnect Spotify** then **Connect Spotify** in the sidebar.")
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

    with st.spinner("Analyzing playlist (cached + rate-limit safe + 403-safe)…"):
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
                st.error("Spotify token expired. Please **Disconnect Spotify** then **Connect Spotify** in the sidebar, then retry.")
                return
            st.error("Spotify returned an error while analyzing.")
            st.caption(f"HTTP status: {status}")
            return

    pl_name = (pl_info or {}).get("name", "Playlist")
    owner = ((pl_info or {}).get("owner") or {}).get("display_name", "")
    st.subheader(f"🎵 {pl_name} — {owner}".strip(" —"))

    # Diagnostics always visible
    with st.expander("🔎 Diagnostics (why you might see no results)", expanded=False):
        st.json(diag)

    if df is None or df.empty:
        st.warning("No playable Spotify tracks were kept after filtering (see Diagnostics).")
        return

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


if option.startswith("1"):
    playlist_input = st.text_input("Enter Spotify Playlist URL or ID:", value="")
    max_tracks = st.number_input("Max tracks (0 = ALL)", min_value=0, value=0, step=10)

    if st.button("🚀 Analyze Playlist"):
        run_analysis(playlist_input, int(max_tracks))

elif option.startswith("2"):
    # Try a stable public playlist for quick validation
    test_url = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
    st.write("Example playlist URL:")
    playlist_input = st.text_input("Test playlist URL/ID", value=test_url)
    max_tracks = st.number_input("Max tracks (0 = ALL)", min_value=0, value=15, step=5)

    if st.button("🧪 Run Test"):
        run_analysis(playlist_input, int(max_tracks))

else:
    st.markdown(
        f"""
**What this does**
- Reads playlist tracks via Spotify API
- Calls Spotify **Audio Features** to get BPM/key
- Outputs BPM + key + mode + Camelot + some DJ-friendly attributes

**Included upgrades**
- Missing BPM/Key % summary
- Rate-limit retry/backoff (429 + transient 5xx)
- Caching (TTL {CACHE_TTL_SECONDS//60} minutes)
- Diagnostics to explain “no results”
        """
    )
