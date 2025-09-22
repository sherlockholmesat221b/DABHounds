# dabhounds/core/dab.py

import time
from typing import Optional, List, Dict
from rapidfuzz import fuzz
import requests

from dabhounds.core.auth import load_config
from dabhounds.core.qobuz import get_qobuz_ids_for_isrc
from dabhounds.core.musicbrainz import resolve_track_metadata

CONFIG = load_config()
API_BASE = CONFIG["DAB_API_BASE"]

# Disable SSL warnings globally (optional)
requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.exceptions.InsecureRequestWarning
)

# --- Rate limiting ---
_LAST_REQUEST_TIME = 0
_MIN_INTERVAL = 10 / 15  # 0.6667 seconds per request

def _throttle():
    global _LAST_REQUEST_TIME
    elapsed = time.time() - _LAST_REQUEST_TIME
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _LAST_REQUEST_TIME = time.time()

# --- Core API calls ---
def search_dab(query: str, token: str) -> List[Dict]:
    """Search DAB for tracks matching the query."""
    _throttle()
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": CONFIG.get(
            "USER_AGENT",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/1337.0.0.0 Safari/537.36"
        ),
    }
    try:
        resp = requests.get(
            f"{API_BASE}/search",
            params={"q": query, "type": "track"},
            headers=headers,
            verify=False
        )
        resp.raise_for_status()
        return resp.json().get("tracks", [])
    except requests.RequestException:
        return []

def find_best_quality_track(tracks: List[Dict]) -> Optional[Dict]:
    """Select the track with the highest sample rate / bit depth."""
    if not tracks:
        return None

    def get_quality(track):
        aq = track.get("audioQuality", {})
        return (aq.get("maximumSampleRate", 0), aq.get("maximumBitDepth", 0))

    return sorted(tracks, key=get_quality, reverse=True)[0]

def search_dab_by_isrc(isrc: str, token: str) -> Optional[Dict]:
    """Search by ISRC, optionally filtering by Qobuz IDs."""
    results = search_dab(isrc, token)
    if not results:
        return None

    qobuz_ids = get_qobuz_ids_for_isrc(isrc)
    if qobuz_ids:
        filtered = [t for t in results if t["id"] in qobuz_ids]
        return find_best_quality_track(filtered or results)

    return find_best_quality_track(results)

# --- Matching modes ---
def match_strict(isrc: str, token: str) -> Optional[Dict]:
    if not isrc:
        return None
    return search_dab_by_isrc(isrc, token)

def match_track_lenient(track: Dict, token: str, threshold: int) -> Optional[Dict]:
    """Lenient matching using ISRC first, then fuzzy title/artist search."""
    isrc = track.get("isrc")
    title = track.get("title")
    artist = track.get("artist")

    # Step 1 — ISRC match
    if isrc:
        result = search_dab_by_isrc(isrc, token)
        if result:
            return result

    # Step 2 — Metadata refinement
    meta = resolve_track_metadata(title, artist) or track
    search_query = f"{meta['artist']} {meta['title']}"

    # Step 3 — Search and fuzzy filter
    results = search_dab(search_query, token)
    if not results:
        return None

    best_score = 0
    best_match = None
    for candidate in results:
        candidate_str = f"{candidate['artist']} {candidate['title']}"
        score = fuzz.token_set_ratio(search_query, candidate_str)
        if score > best_score:
            best_score = score
            best_match = candidate

    if best_match and best_score >= threshold:
        return best_match

    return None

def match_manual(title: str, artist: str, token: str) -> Optional[Dict]:
    """Interactive manual track selection from DAB results."""
    query = f"{artist} {title}"
    results = search_dab(query, token)

    if not results:
        print("[DABHound] No DAB results found.")
        return None

    print(f"\n[DABHound] Manual match for: {artist} - {title}")
    for i, track in enumerate(results):
        print(
            f"{i + 1}. {track['artist']} - {track['title']} "
            f"(Album: {track.get('albumTitle', '-')})"
        )

    while True:
        choice = input("Pick a track [1-N] or Enter to skip: ").strip()
        if not choice:
            return None
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(results):
                return results[idx]
        except ValueError:
            pass
        print("[DABHound] Invalid input.")

def match_track(track: Dict, mode: str, token: str, threshold: int) -> Optional[Dict]:
    """General entry point for track matching."""
    if mode == "strict":
        return match_strict(track.get("isrc"), token)
    elif mode == "lenient":
        return match_track_lenient(track, token, threshold)
    elif mode == "manual":
        return match_manual(track.get("title"), track.get("artist"), token)
    else:
        raise ValueError(f"[DABHound] Unknown match mode: {mode}")