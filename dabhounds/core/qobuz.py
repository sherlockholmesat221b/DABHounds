# dabhounds/core/qobuz.py
import requests

QOBUZ_API = "https://www.qobuz.com/api.json/0.2/track/search"
APP_ID = "798273057"  # your app_id here

def get_qobuz_ids_for_isrc(isrc: str):
    """
    Search official Qobuz API for a track by ISRC and return matching track IDs.
    """
    try:
        params = {
            "query": isrc,
            "limit": 50,  # keep the old default limit
            "app_id": APP_ID
        }
        resp = requests.get(QOBUZ_API, params=params)
        if not resp.ok:
            return []

        data = resp.json()
        tracks = data.get("tracks", {}).get("items", [])
        return [t["id"] for t in tracks if t.get("isrc") == isrc]
    except Exception:
        return []