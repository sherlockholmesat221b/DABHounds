import os
import requests
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urlparse, unquote
from dabhounds.core.auth import load_config

CONFIG = load_config()
API_BASE = CONFIG["DAB_API_BASE"]

def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename.strip()

def get_stream_url(track_id: str, token: str, quality: str = "27") -> Optional[str]:
    """Get streaming URL for a track from DAB API."""
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

    try:
        resp = requests.get(
            f"{API_BASE}/stream",
            params={"trackId": track_id, "quality": quality},
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("url")
    except Exception as e:
        print(f"[DABHound] Failed to get stream URL for track {track_id}: {e}")
        return None

def download_track(track: Dict, token: str, download_dir: str = "downloads") -> bool:
    """Download a single track."""
    track_id = track.get("id")
    if not track_id:
        print(f"[DABHound] No track ID found for: {track.get('title', 'Unknown')}")
        return False

    stream_url = get_stream_url(track_id, token)
    if not stream_url:
        print(f"[DABHound] Failed to get stream URL for: {track.get('artist', 'Unknown')} - {track.get('title', 'Unknown')}")
        return False

    # Create download directory
    Path(download_dir).mkdir(exist_ok=True)

    # Create filename
    artist = sanitize_filename(track.get("artist", "Unknown Artist"))
    title = sanitize_filename(track.get("title", "Unknown Title"))
    album = sanitize_filename(track.get("albumTitle", "Unknown Album"))

    # Try to get file extension from URL
    parsed_url = urlparse(stream_url)
    path = unquote(parsed_url.path)
    ext = os.path.splitext(path)[1] or ".flac"  # Default to .flac if no extension

    filename = f"{artist} - {title}{ext}"
    filepath = os.path.join(download_dir, filename)

    # Check if file already exists
    if os.path.exists(filepath):
        print(f"[DABHound] File already exists, skipping: {filename}")
        return True

    try:
        print(f"[DABHound] Downloading: {artist} - {title}")

        # Download with progress
        response = requests.get(stream_url, stream=True, timeout=30)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\r[DABHound] Progress: {percent:.1f}%", end='', flush=True)

        print(f"\n[DABHound] Downloaded: {filename}")
        return True

    except Exception as e:
        print(f"\n[DABHound] Failed to download {artist} - {title}: {e}")
        # Clean up partial download
        if os.path.exists(filepath):
            os.remove(filepath)
        return False

def get_library_tracks(library_id: str, token: str) -> List[Dict]:
    """Fetch tracks from a DAB library by ID."""
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

    try:
        resp = requests.get(
            f"{API_BASE}/libraries/{library_id}?page=1&limit=2000",
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()

        library = data.get("library", {})
        tracks = library.get("tracks", [])

        print(f"[DABHound] Found library: {library.get('name', 'Unknown')}")
        print(f"[DABHound] Library contains {len(tracks)} tracks")

        return tracks

    except Exception as e:
        print(f"[DABHound] Failed to fetch library {library_id}: {e}")
        return []

def download_tracks(tracks: List[Dict], token: str, download_dir: str = "downloads") -> None:
    """Download multiple tracks."""
    if not tracks:
        print("[DABHound] No tracks to download.")
        return

    print(f"\n[DABHound] Starting download of {len(tracks)} tracks to '{download_dir}' directory...")

    successful = 0
    failed = 0

    for i, track in enumerate(tracks, 1):
        print(f"\n[DABHound] Downloading ({i}/{len(tracks)})")
        if download_track(track, token, download_dir):
            successful += 1
        else:
            failed += 1

    print(f"\n[DABHound] Download complete!")
    print(f"[DABHound] Successfully downloaded: {successful} tracks")
    if failed > 0:
        print(f"[DABHound] Failed to download: {failed} tracks")