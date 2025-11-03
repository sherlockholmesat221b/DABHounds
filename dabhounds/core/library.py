# dabhounds/core/library.py  
  
import requests  
from typing import List  
from dabhounds.core.auth import ensure_logged_in, load_config, get_authenticated_session  
import time  
  
CONFIG = load_config()  
API_BASE = CONFIG["DAB_API_BASE"]  
  
def get_headers():  
    token = ensure_logged_in()  
    return {  
        "Authorization": f"Bearer {token}",  
        "User-Agent": (  
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "  
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/1337.0.0.0 Safari/537.36"  
        )  
    }  

def library_exists(library_id: str) -> bool:
    """Check if a DAB library with this ID still exists."""
    session = get_authenticated_session()
    try:
        response = session.get(f"{API_BASE}/libraries/{library_id}")
        if response.status_code == 200:
            return True
        if response.status_code == 404:
            return False
        # For safety: treat anything else as non-existent
        return False
    except Exception:
        return False

def create_library(name: str, description: str = "", is_public: bool = True) -> str:  
    session = get_authenticated_session()  
    payload = {  
        "name": name,  
        "description": description,  
        "isPublic": is_public  
    }  
    response = session.post(f"{API_BASE}/libraries", json=payload)  
    response.raise_for_status()  
    return response.json()["library"]["id"]  
  
# --- NEW: transform track to API expected format ---  
def transform_track_for_dab(track: dict) -> dict:
    dab = track.get("full_track", {})
    return {
        "id": str(dab.get("id", track.get("dab_track_id", ""))),
        "title": dab.get("title", track.get("title", "")),
        "artist": dab.get("artist", track.get("artist", "")),
        "artistId": dab.get("artistId", 0),
        "albumTitle": dab.get("albumTitle", ""),
        "albumCover": dab.get("albumCover", ""),
        "albumId": dab.get("albumId", ""),
        "releaseDate": dab.get("releaseDate", ""),
        "genre": dab.get("genre", ""),
        "duration": dab.get("duration", 0),
        "audioQuality": dab.get(
            "audioQuality",
            {"maximumBitDepth": 24, "maximumSamplingRate": 96, "isHiRes": True}
        ),
    }
  
def add_tracks_to_library(library_id: str, tracks: List[dict]) -> None:  
    session = get_authenticated_session()  
    min_interval = 10 / 15  # ~0.6667 seconds per request  
    last_request = 0  
  
    for track in tracks:  
        payload = {"track": transform_track_for_dab(track)}  
  
        elapsed = time.time() - last_request  
        if elapsed < min_interval:  
            time.sleep(min_interval - elapsed)  
  
        response = session.post(f"{API_BASE}/libraries/{library_id}/tracks", json=payload)  
        last_request = time.time()  
  
        if not response.ok:  
            print(f"[DABHound] Warning: Failed to add {track['title']} - {track['artist']}")