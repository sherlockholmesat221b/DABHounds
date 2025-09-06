#dabhounds/ core/qobuz.py

import requests

QOBUZ_API = "https://qobuz.squid.wtf/api/get-music"

def get_qobuz_ids_for_isrc(isrc: str):
    try:
        resp = requests.get(f"{QOBUZ_API}?q={isrc}&offset=0&limit=50")
        if not resp.ok:
            return []
        data = resp.json()
        tracks = data.get("data", {}).get("tracks", {}).get("items", [])
        return [t["id"] for t in tracks if t.get("isrc") == isrc]
    except Exception:
        return []
