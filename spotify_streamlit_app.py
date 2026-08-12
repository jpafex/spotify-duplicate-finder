import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from spotipy.cache_handler import CacheHandler
import pandas as pd
from math import ceil
import io
import zipfile
import time
import re
import unicodedata
import requests
import random
from collections import defaultdict
from datetime import datetime
import secrets
import json

# Cookie manager (encrypted)
from streamlit_cookies_manager import EncryptedCookieManager

APP_VERSION = "3.0.3"

# Page config (keep early)
st.set_page_config(page_title="AfexCloud Dashboard", page_icon="☁️", layout="wide")

# ----------------------------
# ENCRYPTED COOKIE SETUP (MUST BE EARLY)
# ----------------------------
# You MUST set COOKIES_PASSWORD in Streamlit secrets for cloud deployments.
cookies = EncryptedCookieManager(
    prefix="afexcloud/",
    password=st.secrets.get("COOKIES_PASSWORD", "CHANGE_ME_SET_COOKIES_PASSWORD"),
)

# Streamlit cookie components require readiness check.
if not cookies.ready():
    st.stop()

SPOTIFY_COOKIE_KEY = "spotify_token_info_v1"

# ----------------------------
# 1) GLOBAL STATE INITIALIZATION
# ----------------------------
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False
if "global_proj" not in st.session_state:
    st.session_state["global_proj"] = ""

# Spotify OAuth session state
if "spotify_token_info" not in st.session_state:
    st.session_state["spotify_token_info"] = None
if "spotify_oauth_state" not in st.session_state:
    # Persist a stable state per Streamlit session to reduce OAuth flakiness.
    st.session_state["spotify_oauth_state"] = secrets.token_urlsafe(16)

# ----------------------------
# 2) SECURE LOGIN GATE
# ----------------------------
def check_password() -> bool:
    if st.session_state.get("password_correct"):
        return True

    st.title("🔐 AfexCloud Tool Login")
    with st.form("login_form"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if u == st.secrets["APP_USER"] and p == st.secrets["APP_PASS"]:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Invalid credentials.")
    return False


# ----------------------------
# 3) SPOTIFY AUTH (SESSION + ENCRYPTED COOKIE)
# ----------------------------
def _load_token_from_cookie():
    raw = cookies.get(SPOTIFY_COOKIE_KEY)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _save_token_to_cookie(token_info: dict):
    try:
        cookies[SPOTIFY_COOKIE_KEY] = json.dumps(token_info)
        cookies.save()
    except Exception:
        # If cookie write fails for any reason, we still keep session_state working.
        pass


def _clear_token_cookie():
    # Some cookie managers can be finicky about deletion; do both delete and blank-set.
    try:
        if SPOTIFY_COOKIE_KEY in cookies:
            del cookies[SPOTIFY_COOKIE_KEY]
        cookies.save()
    except Exception:
        pass
    try:
        cookies[SPOTIFY_COOKIE_KEY] = ""
        cookies.save()
    except Exception:
        pass


class StreamlitSessionCookieCacheHandler(CacheHandler):
    """
    Spotipy cache handler that:
    - reads token from session_state first
    - falls back to encrypted cookie
    - saves to both session_state and cookie
    This provides:
    - no shared .cache-token collisions
    - persistence across refresh/new tab/browser restart
    """
    def __init__(self, session_key: str = "spotify_token_info"):
        self.session_key = session_key

    def get_cached_token(self):
        tok = st.session_state.get(self.session_key)
        if tok:
            return tok

        tok = _load_token_from_cookie()
        if tok:
            st.session_state[self.session_key] = tok
            return tok

        return None

    def save_token_to_cache(self, token_info):
        st.session_state[self.session_key] = token_info
        _save_token_to_cookie(token_info)

    def delete_cached_token(self):
        st.session_state[self.session_key] = None
        _clear_token_cookie()


def get_auth_manager() -> SpotifyOAuth:
    scope = "playlist-modify-public playlist-modify-private playlist-read-private"
    cache_handler = StreamlitSessionCookieCacheHandler()

    return SpotifyOAuth(
        client_id=st.secrets["SPOTIFY_CLIENT_ID"],
        client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"],
        redirect_uri=st.secrets["SPOTIFY_REDIRECT_URI"],
        scope=scope,
        open_browser=False,
        cache_handler=cache_handler,
        state=st.session_state["spotify_oauth_state"],
        show_dialog=True,
    )


def get_query_params():
    try:
        return dict(st.query_params)
    except Exception:
        return st.experimental_get_query_params()


def clear_query_params():
    try:
        st.query_params.clear()
    except Exception:
        st.experimental_set_query_params()


def handle_spotify_callback(auth_manager: SpotifyOAuth) -> None:
    qp = get_query_params()

    if "error" in qp:
        st.error(f"Spotify authorization error: {qp.get('error')}")
        clear_query_params()
        return

    code = None
    state = None

    if "code" in qp:
        code = qp["code"][0] if isinstance(qp["code"], list) else qp["code"]
    if "state" in qp:
        state = qp["state"][0] if isinstance(qp["state"], list) else qp["state"]

    if not code:
        return

    expected_state = st.session_state.get("spotify_oauth_state")
    if expected_state and state and state != expected_state:
        st.warning("Spotify login validation failed (state mismatch). Please click 'Connect Spotify' again.")
        clear_query_params()
        st.session_state["spotify_oauth_state"] = secrets.token_urlsafe(16)
        return

    try:
        # Exchange code for token_info (cache_handler persists it)
        auth_manager.get_access_token(code, check_cache=False, as_dict=True)
        clear_query_params()
        st.rerun()  # critical: immediate UI update
    except Exception as e:
        st.error("Spotify login failed. Please try again.")
        st.caption(f"Details: {e}")
        clear_query_params()


def get_valid_token_info(auth_manager: SpotifyOAuth):
    """
    Checks if a valid token exists, handles automatic background refreshes,
    and safely discards expired tokens to prevent 2026 invalid_grant crashes.
    """
    try:
        # 1. Attempt to grab and validate the cached token
        # (Spotipy naturally attempts a background refresh here if expired)
        token_info = auth_manager.get_cached_token()
       
        if token_info:
            return token_info
           
    except Exception as e:
        # 2. THE 2026 SAFEGUARD: Catch the 6-month expiration error [cite: 3, 5]
        if "invalid_grant" in str(e).lower():
            st.warning("🔄 Your 6-month Spotify access has expired. Clearing dead session...")
           
            # 3. Discard the expired token immediately [cite: 4, 6]
            if "spotify_token" in st.session_state:
                st.session_state["spotify_token"] = None
               
            # If your app uses a local cache file, wipe it clean [cite: 4, 6]
            try:
                if os.path.exists(".cache"):
                    os.remove(".cache")
            except Exception:
                pass
               
            # Return None so the app knows it must show the login button
            return None
        else:
            # Pass along any unrelated network or API errors
            st.error(f"Spotify token validation failed: {e}")
            return None
           
    return None


# ----------------------------
# 4) HELPERS
# ----------------------------
def advanced_normalize(text):
    if not isinstance(text, str):
        text = str(text)
    try:
        text = text.encode("cp1252").decode("utf-8")
    except Exception:
        pass
    text = unicodedata.normalize("NFKD", text)
    text = "".join([c for c in text if not unicodedata.combining(c)])
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def get_playlist_metadata(url_or_id):
    sp_read = spotipy.Spotify(
        auth_manager=SpotifyClientCredentials(
            client_id=st.secrets["SPOTIFY_CLIENT_ID"],
            client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"],
        )
    )
    p_id = url_or_id.split("/")[-1].split("?")[0] if "/" in url_or_id else url_or_id
    try:
        meta = sp_read.playlist(p_id, fields="name")
        p_name = meta["name"]
        tracks = []
        results = sp_read.playlist_tracks(p_id)
        pos = 1
        while results:
            for item in results["items"]:
                if item.get("track"):
                    t = item["track"]
                    tracks.append(
                        {
                            "Original Pos": pos,
                            "Spotify - id": t.get("id"),
                            "Name": t.get("name", "Unknown"),
                            "Artist": t["artists"][0]["name"] if t.get("artists") else "Unknown",
                            "Album": t["album"]["name"] if t.get("album") else "Unknown",
                        }
                    )
                    pos += 1
            results = sp_read.next(results) if results.get("next") else None
        return p_name, tracks
    except Exception:
        return "Unknown", []


def hunt_dna(name, artist):
    query = f"{name} {artist}".replace(" ", "+")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # Source 1: Tunebat Deep Hunt
    try:
        r = requests.get(f"https://tunebat.com/Search?q={query}", headers=headers, timeout=8)
        match = re.search(r'href="(/Info/[^"]+)"', r.text)
        if match:
            time.sleep(random.uniform(0.5, 1.2))
            r_info = requests.get(f"https://tunebat.com{match.group(1)}", headers=headers, timeout=8)
            key = re.search(r">Key<.*?secondary-label\">([^<]+)", r_info.text, re.S)
            bpm = re.search(r">BPM<.*?secondary-label\">([^<]+)", r_info.text, re.S)
            if key and bpm:
                return key.group(1).strip(), bpm.group(1).strip(), "Tunebat"
    except Exception:
        pass

    # Source 2: GetSongBPM Fallback
    try:
        r_gsb = requests.get(f"https://getsongbpm.com/search?q={query}", headers=headers, timeout=8)
        key = re.search(r'data-key="([^"]+)"', r_gsb.text)
        bpm = re.search(r'data-bpm="(\d+)"', r_gsb.text)
        if key and bpm:
            return key.group(1).strip(), bpm.group(1).strip(), "GetSongBPM"
    except Exception:
        pass

    return "Not Found", "Not Found", "None"


# ----------------------------
# MAIN APP
# ----------------------------
if check_password():
    auth_manager = get_auth_manager()

    # Handle OAuth callback BEFORE computing token state
    handle_spotify_callback(auth_manager)

    token_info = get_valid_token_info(auth_manager)

    with st.sidebar:
        st.title("☁️ AfexCloud")
        st.caption(f"v{APP_VERSION}")
        st.write("---")

        st.session_state["global_proj"] = st.text_input("📁 Global Project:", value=st.session_state["global_proj"])
        if st.button("🔄 Reset Project"):
            st.session_state["global_proj"] = ""
            st.rerun()

        st.write("---")

        if token_info:
            st.success("🟢 Spotify: Connected")
            if st.button("🔌 Disconnect Spotify"):
                auth_manager.cache_handler.delete_cached_token()
                st.session_state["spotify_oauth_state"] = secrets.token_urlsafe(16)
                clear_query_params()
                st.rerun()
        else:
            st.error("🔴 Spotify: Not Connected")
            auth_url = auth_manager.get_authorize_url()
            try:
                st.link_button("Connect Spotify", auth_url)
            except Exception:
                st.markdown(f"[Connect Spotify]({auth_url})")

        choice = st.radio(
            "Select a Tool:",
            [
                "🏠 Home",
                "🔍 Duplicate Finder",
                "📋 Song Lister",
                "📦 Batch Manager",
                "💿 Library Auditor",
                "📊 Collection Reviewer",
                "🗑️ Playlist Deleter",
                "🕵️ Sidecar Scraper",
            ],
        )

        st.write("---")
        if st.button("🚪 Log Out"):
            st.session_state["password_correct"] = False
            # Optional: also disconnect Spotify on logout
            auth_manager.cache_handler.delete_cached_token()
            st.session_state["spotify_oauth_state"] = secrets.token_urlsafe(16)
            clear_query_params()
            st.rerun()

    safe_proj = re.sub(r"[^a-zA-Z0-9_]", "_", st.session_state["global_proj"])

    # --- TOOLS ---
    if choice == "🏠 Home":
        st.title("🚀 AfexCloud Dashboard")
        st.info(f"Active Project: **{st.session_state['global_proj'] if st.session_state['global_proj'] else 'None Set'}**")

    elif choice == "🔍 Duplicate Finder":
        st.title(f"🔍 Duplicate Finder: {st.session_state['global_proj']}")
        url = st.text_input("Enter Playlist URL/ID:")
        if st.button("Scan"):
            p_name, tracks = get_playlist_metadata(url)
            if tracks:
                by_id = defaultdict(list)
                for t in tracks:
                    by_id[t["Spotify - id"]].append(t)
                dupes = [i for g in by_id.values() if len(g) > 1 for i in g]
                if dupes:
                    st.warning(f"Found {len(dupes)} duplicates.")
                    df_dupes = pd.DataFrame(dupes)
                    st.dataframe(df_dupes, use_container_width=True, hide_index=True)
                    st.download_button(
                        "📥 Download Dupes",
                        df_dupes.to_csv(index=False).encode("utf-8"),
                        f"{safe_proj}_dupes.csv",
                        "text/csv",
                    )
                else:
                    st.success("No duplicates found!")

    elif choice == "📋 Song Lister":
        st.title(f"📋 Song Lister: {st.session_state['global_proj']}")
        url = st.text_input("Enter Playlist URL/ID:")
        if st.button("Generate Inventory"):
            p_name, tracks = get_playlist_metadata(url)
            if tracks:
                df = pd.DataFrame(tracks)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.download_button(
                    "📥 Download Inventory",
                    df.to_csv(index=False).encode("utf-8"),
                    f"{safe_proj}_inventory.csv",
                    "text/csv",
                )

    elif choice == "📦 Batch Manager":
        st.title(f"📦 Batch Manager: {st.session_state['global_proj']}")
        tab1, tab2 = st.tabs(["Step 1: Create Batches", "Step 2: Upload"])

        with tab1:
            url = st.text_input("Source Playlist URL/ID:")
            if st.button("Generate Batches"):
                p_name, all_tracks = get_playlist_metadata(url)
                if all_tracks:
                    num_batches = ceil(len(all_tracks) / 25)
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w") as zf:
                        for i in range(num_batches):
                            batch = all_tracks[i * 25 : (i + 1) * 25]
                            df_batch = pd.DataFrame(batch)[["Original Pos", "Name", "Artist", "Album", "Spotify - id"]]
                            lbl = f"{batch[0]['Original Pos']}_to_{batch[-1]['Original Pos']}"
                            zf.writestr(
                                f"{safe_proj}_Batch_{i+1}_{lbl}.csv",
                                df_batch.to_csv(index=False).encode("utf-8"),
                            )
                    st.download_button(
                        "📦 DOWNLOAD ZIP",
                        zip_buffer.getvalue(),
                        f"{safe_proj}_Batches.zip",
                        "application/zip",
                    )

        with tab2:
            if not token_info:
                st.warning("Connect Spotify first.")
            else:
                files = st.file_uploader("Upload Batch CSVs", accept_multiple_files=True, type="csv")
                if st.button("🚀 Create Spotify Playlists"):
                    if not files:
                        st.warning("Please upload at least one CSV batch file.")
                    else:
                        sp_write = spotipy.Spotify(auth_manager=auth_manager)
                        user_id = sp_write.current_user()["id"]
                        for uploaded in files:
                            df = pd.read_csv(uploaded)
                            playlist = sp_write.user_playlist_create(
                                user=user_id,
                                name=f"{st.session_state['global_proj']}: {uploaded.name}",
                                public=False,
                            )
                            track_uris = [f"spotify:track:{tid}" for tid in df["Spotify - id"].tolist()]
                            for start in range(0, len(track_uris), 100):
                                sp_write.playlist_add_items(playlist["id"], track_uris[start : start + 100])
                        st.balloons()

    elif choice == "💿 Library Auditor":
        st.title(f"💿 Library Auditor: {st.session_state['global_proj']}")
        c1, c2 = st.columns(2)
        with c1:
            inv_f = st.file_uploader("Spotify Inventory", type="csv")
        with c2:
            loc_f = st.file_uploader("Local Songs", type="csv")

        if inv_f and loc_f:
            if st.button("🔍 Run Audit"):
                df_inv, df_loc = pd.read_csv(inv_f), pd.read_csv(loc_f)
                df_inv["compare_key"] = df_inv.apply(
                    lambda r: f"{advanced_normalize(r['Name'])}__{advanced_normalize(r['Artist'])}", axis=1
                )
                loc_keys = {
                    f"{advanced_normalize(str(e).split(',')[0])}__{advanced_normalize(str(e).split(',')[1])}"
                    for e in df_loc.iloc[:, 0]
                    if len(str(e).split(",")) >= 2
                }
                missing_df = df_inv[~df_inv["compare_key"].isin(loc_keys)].copy()
                st.metric("Missing Tracks", len(missing_df))
                st.dataframe(missing_df[["Original Pos", "Name", "Artist", "Album"]], use_container_width=True, hide_index=True)
                st.download_button(
                    "📥 Download Missing",
                    missing_df.to_csv(index=False).encode("utf-8"),
                    f"{safe_proj}_Missing.csv",
                    "text/csv",
                )

    elif choice == "📊 Collection Reviewer":
        st.title(f"📊 Collection Reviewer: {st.session_state['global_proj']}")
        c1, c2 = st.columns(2)
        with c1:
            inv_f = st.file_uploader("Inventory", type="csv")
        with c2:
            loc_f = st.file_uploader("Local Library", type="csv")

        if inv_f and loc_f:
            if st.button("📊 Generate Smart Review"):
                df_inv, df_loc = pd.read_csv(inv_f), pd.read_csv(loc_f)
                inv_rows = [
                    {
                        "Source": "Spotify",
                        "Key": f"{advanced_normalize(r['Name'])}__{advanced_normalize(r['Artist'])}",
                        "Name": r["Name"],
                        "Artist": r["Artist"],
                    }
                    for _, r in df_inv.iterrows()
                ]
                loc_rows = []
                for e in df_loc.iloc[:, 0]:
                    p = str(e).split(",")
                    if len(p) >= 2:
                        loc_rows.append(
                            {
                                "Source": "Local",
                                "Key": f"{advanced_normalize(p[0])}__{advanced_normalize(p[1])}",
                                "Name": p[0],
                                "Artist": p[1],
                            }
                        )
                master_df = pd.concat([pd.DataFrame(inv_rows), pd.DataFrame(loc_rows)]).sort_values(
                    by=["Key", "Source"]
                ).reset_index(drop=True)
                counts = master_df["Key"].value_counts()
                lone_wolf_keys = counts[counts == 1].index.tolist()
                st.metric("Mismatches", len(lone_wolf_keys), delta_color="inverse")
                st.dataframe(master_df, use_container_width=True, hide_index=True)
                st.download_button(
                    "📥 Download Report",
                    master_df.to_csv(index=False).encode("utf-8"),
                    f"{safe_proj}_Health.csv",
                    "text/csv",
                )

    elif choice == "🗑️ Playlist Deleter":
        st.title("🗑️ Playlist Deleter")
        if not token_info:
            st.warning("Connect Spotify first.")
        else:
            sp = spotipy.Spotify(auth_manager=auth_manager)
            if st.button("🔍 Load My Playlists"):
                st.session_state["my_playlists"] = sp.current_user_playlists(limit=50)["items"]
            if "my_playlists" in st.session_state:
                with st.form("del_form"):
                    to_del = []
                    for p in st.session_state["my_playlists"]:
                        if st.checkbox(f"{p['name']} (ID: {p['id']})"):
                            to_del.append({"id": p["id"], "name": p["name"]})
                    if st.form_submit_button("🔥 DELETE SELECTED"):
                        for item in to_del:
                            sp.current_user_unfollow_playlist(item["id"])
                        st.success(f"Deleted {len(to_del)} playlists.")
                        log = pd.DataFrame(to_del)
                        st.download_button(
                            "📥 Download Deletion Proof",
                            log.to_csv(index=False).encode("utf-8"),
                            f"Deletion_Proof_{datetime.now().strftime('%Y%m%d')}.csv",
                            "text/csv",
                        )
                        del st.session_state["my_playlists"]
                        st.rerun()

    elif choice == "🕵️ Sidecar Scraper":
        st.title(f"🕵️ Sidecar Musical Scraper (v{APP_VERSION})")
        st.info("No API Costs. Using public music databases to build your DNA logs.")
        inv_f = st.file_uploader("Upload Inventory CSV", type="csv")

        if inv_f:
            df_inv = pd.read_csv(inv_f)
            if st.button("🚀 Start Multi-Source Scrape"):
                results, prog = [], st.progress(0)
                status_text = st.empty()
                for i, row in df_inv.iterrows():
                    status_text.write(f"Scraping ({i+1}/{len(df_inv)}): **{row['Name']}**")
                    k, b, src = hunt_dna(row["Name"], row["Artist"])
                    results.append({"Key": k, "BPM": b, "Source": src})
                    prog.progress((i + 1) / len(df_inv))
                    time.sleep(random.uniform(0.8, 1.5))

                df_final = pd.concat([df_inv, pd.DataFrame(results)], axis=1)
                st.success("DNA Hunt Complete!")
                st.dataframe(df_final, use_container_width=True, hide_index=True)
                st.download_button(
                    "📥 Download Master DJ Log",
                    df_final.to_csv(index=False).encode("utf-8"),
                    f"{safe_proj}_Master_DJ_Log.csv",
                    "text/csv",
                )

# --- FINAL FOOTER ---
st.write("---")
cur_p = st.session_state.get("global_proj", "Default")
st.caption(f"AfexCloud v{APP_VERSION} | Project: {cur_p if cur_p else 'Default'} | Multi-Source Scraper Active")
