import os
import sys
import time
import threading
import unicodedata
import requests
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse, unquote
from tqdm import tqdm

from dabhounds.core.auth import load_config
from dabhounds.core.tagger import tag_audio
from dabhounds.core.cover import download_cover_image  # you’d need to add this

CONFIG = load_config()
API_BASE = CONFIG["DAB_API_BASE"]

# --- State flags ---
_PAUSED = False
_STOPPED = False
_CURRENT_PBAR = None


# --- Keyboard listener (cross-platform) ---
def _keypress_listener():
    """Thread: watches keyboard input for pause/resume/stop."""
    global _PAUSED, _STOPPED

    if os.name == "nt":  # Windows
        import msvcrt
        while not _STOPPED:
            if msvcrt.kbhit():
                key = msvcrt.getch().decode(errors="ignore").lower()
                if key == "p":
                    _PAUSED = not _PAUSED
                    tqdm.write("[Downloader] Paused" if _PAUSED else "[Downloader] Resumed")
                    if _CURRENT_PBAR and not _PAUSED:
                        _CURRENT_PBAR.refresh()
                elif key == "q":
                    _STOPPED = True
                    tqdm.write("[Downloader] Stopped by user")
            time.sleep(0.1)
    else:  # POSIX
        import termios, tty, select
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        try:
            while not _STOPPED:
                dr, _, _ = select.select([sys.stdin], [], [], 0.1)
                if dr:
                    key = sys.stdin.read(1).lower()
                    if key == "p":
                        _PAUSED = not _PAUSED
                        tqdm.write("[Downloader] Paused" if _PAUSED else "[Downloader] Resumed")
                        if _CURRENT_PBAR and not _PAUSED:
                            _CURRENT_PBAR.refresh()
                    elif key == "q":
                        _STOPPED = True
                        tqdm.write("[Downloader] Stopped by user")
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _start_controls():
    t = threading.Thread(target=_keypress_listener, daemon=True)
    t.start()


def _wait_if_paused():
    global _PAUSED, _STOPPED
    while _PAUSED and not _STOPPED:
        time.sleep(0.2)


# --- Filename utilities ---
def _sanitize_filename(name: str) -> str:
    name = unicodedata.normalize("NFKC", name)
    return "".join(c for c in name if c.isalnum() or c in " -_()[]{}.,").strip() or "untitled"


def _format_filename(track: dict, index: int = None, ext: str = "flac") -> str:
    title = _sanitize_filename(track.get("title") or "untitled")
    if index is not None:
        return f"{index:02d} - {title}.{ext}"
    return f"{title}.{ext}"


# --- API helpers ---
def get_stream_url(track_id: str, token: str, quality: str = "27") -> Optional[str]:
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
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("url")
    except Exception as e:
        tqdm.write(f"[Downloader] Failed to get stream URL for {track_id}: {e}")
        return None


def fetch_all_tracks(library_id: str, token: str, limit: int = 100) -> List[Dict]:
    """Fetch all tracks from a library with pagination."""
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
    page = 1
    all_tracks = []
    while True:
        try:
            resp = requests.get(
                f"{API_BASE}/libraries/{library_id}?page={page}&limit={limit}",
                headers=headers,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            tqdm.write(f"[Downloader] Failed to fetch library page {page}: {e}")
            break

        library = data.get("library", {})
        tracks = library.get("tracks", [])
        if not tracks:
            break

        all_tracks.extend(tracks)
        if len(tracks) < limit:
            break
        page += 1

    return all_tracks


# --- Main download ---
def download_track(track: dict, token: str, directory: str, index: int = None, quality: str = "27") -> Optional[str]:
    global _CURRENT_PBAR, _PAUSED, _STOPPED
    _PAUSED = False
    _STOPPED = False
    _CURRENT_PBAR = None

    track_id = track.get("id")
    if not track_id:
        tqdm.write("[Downloader] Missing track ID.")
        return None

    ext = "flac" if quality == "27" else "mp3"
    filename = _format_filename(track, index=index, ext=ext)
    filepath = os.path.join(directory, filename)

    if os.path.exists(filepath):
        tqdm.write(f"[Downloader] Skipped (exists): {filepath}")
        return filepath

    stream_url = get_stream_url(track_id, token, quality=quality)
    if not stream_url:
        return None

    tqdm.write(f"[Downloader] Downloading: {filepath}")
    tqdm.write("[Controls] Press 'p' = Pause/Resume | 'q' = Stop")

    _start_controls()

    try:
        with requests.get(stream_url, stream=True, timeout=30) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            with open(filepath, "wb") as f, tqdm(
                total=total,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc="Downloading",
                ncols=70,
                disable=not CONFIG.get("SHOW_PROGRESS", True),
            ) as pbar:
                _CURRENT_PBAR = pbar
                for chunk in r.iter_content(chunk_size=8192):
                    if _STOPPED:
                        tqdm.write("[Downloader] Stopped by user before completion.")
                        _CURRENT_PBAR = None
                        return None
                    _wait_if_paused()
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))

        tqdm.write("[Downloader] Download completed.")
        return filepath

    except Exception as e:
        tqdm.write(f"[Downloader] Download failed: {e}")
        if os.path.exists(filepath):
            os.remove(filepath)
        return None


def download_library(library_id: str, token: str, quality: str = "27", output_dir: str = "downloads") -> None:
    tracks = fetch_all_tracks(library_id, token)
    if not tracks:
        tqdm.write("[Library] No tracks found.")
        return

    library_name = _sanitize_filename(f"library_{library_id}")
    lib_folder = os.path.join(output_dir, f"{library_name} [{quality}]")
    os.makedirs(lib_folder, exist_ok=True)

    tqdm.write(f"[Library] Downloading: {library_name} ({len(tracks)} tracks)")

    playlist_paths = []
    for idx, track in enumerate(tracks, 1):
        tqdm.write(f"[{idx}/{len(tracks)}] {track.get('title')} — {track.get('artist')}")
        raw_path = download_track(track, token, lib_folder, index=idx, quality=quality)
        if not raw_path:
            tqdm.write("[Library] Skipping: download failed.")
            continue

        # Cover + tagging
        cover_url = track.get("albumCover")
        cover_path = None
        if cover_url:
            clean_title = _sanitize_filename(track.get("title", "cover"))
            cover_path = download_cover_image(cover_url, os.path.join(lib_folder, f"{clean_title}.jpg"))

        metadata = {
            "title": track.get("title", ""),
            "artist": track.get("artist", ""),
            "album": track.get("albumTitle", ""),
            "genre": track.get("genre", ""),
            "date": track.get("releaseDate", "")[:4],
        }
        tag_audio(raw_path, metadata, cover_path=cover_path)

        if cover_path and os.path.exists(cover_path) and not CONFIG.get("KEEP_COVER_FILE", False):
            try:
                os.remove(cover_path)
            except Exception:
                pass

        playlist_paths.append(os.path.basename(raw_path))

    # Write playlist
    m3u_path = os.path.join(lib_folder, "library.m3u8")
    with open(m3u_path, "w", encoding="utf-8") as m3u:
        for filename in playlist_paths:
            m3u.write(filename + "\n")

    tqdm.write(f"[Library] Finished: {len(playlist_paths)} tracks saved to {lib_folder}")
    tqdm.write(f"[Library] Playlist written to: {m3u_path}")