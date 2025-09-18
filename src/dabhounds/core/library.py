# dabhounds/core/library.py

import requests
from typing import List

from dabhounds.core.auth import ensure_logged_in, load_config, get_authenticated_session   

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

    response = requests.post(f"{API_BASE}/libraries", json=payload, headers=headers)
    response.raise_for_status()
    return response.json()["library"]["id"]

def add_tracks_to_library(library_id: str, tracks: List[dict]) -> None:
    session = get_authenticated_session()
    for track in tracks:
        payload = {"track": track}
        response = session.post(f"{API_BASE}/libraries/{library_id}/tracks", json=payload)
        if not response.ok:
            print(f"[DABHound] Warning: Failed to add {track['title']} - {track['artist']}")
