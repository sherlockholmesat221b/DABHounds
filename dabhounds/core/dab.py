# dabhounds/core/dab.py

import requests
from typing import Optional, List, Dict
from rapidfuzz import fuzz

from dabhounds.core.auth import load_config
from dabhounds.core.qobuz import get_qobuz_ids_for_isrc
from dabhounds.core.musicbrainz import resolve_track_metadata

CONFIG = load_config()
API_BASE = CONFIG["DAB_API_BASE"]

# Disable SSL warnings globally (optional)
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)


def search_dab(query: str, token) -> List[Dict]:
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": CONFIG.get(
            "USER_AGENT",
            (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/1337.0.0.0 Safari/537.36"
            )
        ),
    }
    resp = requests.get(
        f"{API_BASE}/search",
        params={"q": query, "type": "track"},
        headers=headers,
        verify=False  # SSL verification disabled
    )
    if not resp.ok:
        return []
    return resp.json().get("tracks", [])


def find_best_quality_track(tracks: List[Dict]) -> Optional[Dict]:
    if not tracks:
        return None

    def get_quality(track):
        aq = track.get("audioQuality", {})
        return (
            aq.get("maximumSampleRate", 0),
            aq.get("maximumBitDepth", 0)
        )

    return sorted(tracks, key=get_quality, reverse=True)[0]


def search_dab_by_isrc(isrc: str, token) -> Optional[Dict]:
    results = search_dab(isrc, token)
    if not results:
        return None

    qobuz_ids = get_qobuz_ids_for_isrc(isrc)
    if qobuz_ids:
        filtered = [t for t in results if t["id"] in qobuz_ids]
        return find_best_quality_track(filtered or results)
    
    return find_best_quality_track(results)


def match_strict(isrc: str, token) -> Optional[Dict]:
    if not isrc:
        return None
    return search_dab_by_isrc(isrc, token)


def match_track_lenient(track: Dict, token, threshold: int) -> Optional[Dict]:
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


def match_manual(title: str, artist: str, token) -> Optional[Dict]:
    query = f"{artist} {title}"
    results = search_dab(query, token)

    if not results:
        print("[DABHound] No DAB results found.")
        return None

    print(f"\n[DABHound] Manual match for: {artist} - {title}")
    for i, track in enumerate(results):
        print(f"{i + 1}. {track['artist']} - {track['title']} (Album: {track.get('albumTitle', '-')})")

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


def match_track(track: Dict, mode: str, token, threshold: int) -> Optional[Dict]:
    if mode == "strict":
        return match_strict(track.get("isrc"), token)
    elif mode == "lenient":
        return match_track_lenient(track, token, threshold)
    elif mode == "manual":
        return match_manual(track.get("title"), track.get("artist"), token)
    else:
        raise ValueError(f"[DABHound] Unknown match mode: {mode}")
    def get_quality(track):
        aq = track.get("audioQuality", {})
        return (
            aq.get("maximumSampleRate", 0),
            aq.get("maximumBitDepth", 0)
        )

    return sorted(tracks, key=get_quality, reverse=True)[0]


def search_dab_by_isrc(isrc: str, token) -> Optional[Dict]:
    results = search_dab(isrc, token)
    if not results:
        return None

    qobuz_ids = get_qobuz_ids_for_isrc(isrc)
    if qobuz_ids:
        filtered = [t for t in results if t["id"] in qobuz_ids]
        return find_best_quality_track(filtered or results)
    
    return find_best_quality_track(results)


def match_strict(isrc: str, token) -> Optional[Dict]:
    if not isrc:
        return None
    return search_dab_by_isrc(isrc, token)


def match_track_lenient(track: Dict, token, threshold: int) -> Optional[Dict]:
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


def match_manual(title: str, artist: str, token) -> Optional[Dict]:
    query = f"{artist} {title}"
    results = search_dab(query, token)

    if not results:
        print("[DABHound] No DAB results found.")
        return None

    print(f"\n[DABHound] Manual match for: {artist} - {title}")
    for i, track in enumerate(results):
        print(f"{i + 1}. {track['artist']} - {track['title']} (Album: {track.get('albumTitle', '-')})")

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


def match_track(track: Dict, mode: str, token, threshold: int) -> Optional[Dict]:
    if mode == "strict":
        return match_strict(track.get("isrc"), token)
    elif mode == "lenient":
        return match_track_lenient(track, token, threshold)
    elif mode == "manual":
        return match_manual(track.get("title"), track.get("artist"), token)
    else:
        raise ValueError(f"[DABHound] Unknown match mode: {mode}")
