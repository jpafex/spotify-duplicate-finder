import re
import time
import random
import unicodedata
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

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

def get_playlist_metadata(url_or_id, client_id: str, client_secret: str):
    sp_read = spotipy.Spotify(
        auth_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
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
    headers = {"User-Agent": "Mozilla/5.0"}
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

    try:
        r_gsb = requests.get(f"https://getsongbpm.com/search?q={query}", headers=headers, timeout=8)
        key = re.search(r'data-key="([^"]+)"', r_gsb.text)
        bpm = re.search(r'data-bpm="(\d+)"', r_gsb.text)
        if key and bpm:
            return key.group(1).strip(), bpm.group(1).strip(), "GetSongBPM"
    except Exception:
        pass

    return "Not Found", "Not Found", "None"

