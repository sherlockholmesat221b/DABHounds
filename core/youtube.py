# core/youtube.py

from typing import List, Dict
import yt_dlp
import re
import os

from core.musicbrainz import resolve_track_metadata

class YouTubeFetcher:
    def __init__(self):
        self.ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": False,
            "force_generic_extractor": False,
        }

    def _sanitize_filename(self, name: str) -> str:
        """Remove invalid filename characters and strip spaces."""
        return re.sub(r'[<>:"/\\|?*\x00-\x1F]', '', name).strip()

    def extract_tracks(self, url: str) -> List[Dict]:
        """Extract track metadata from a YouTube video/playlist."""
        tracks = []
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            if "entries" in info:
                entries = info["entries"]
            else:
                entries = [info]

            for entry in entries:
                if not entry:
                    continue

                title = entry.get("title", "").strip()
                artist = entry.get("uploader", "").strip()
                isrc = entry.get("isrc")
                duration_sec = entry.get("duration")
                youtube_id = entry.get("id")

                # Sanitize for any later use in filenames/reports
                safe_title = self._sanitize_filename(title)
                safe_artist = self._sanitize_filename(artist)

                # Try MusicBrainz if ISRC missing or uncertain
                if not isrc and safe_title and safe_artist:
                    mb_data = resolve_track_metadata(safe_title, safe_artist)
                    if mb_data:
                        # Replace with higher-confidence metadata
                        title = mb_data.get("title", title)
                        artist = mb_data.get("artist", artist)
                        isrc = mb_data.get("isrc", isrc)
                        if not duration_sec and mb_data.get("duration_ms"):
                            duration_sec = int(mb_data["duration_ms"] / 1000)

                tracks.append({
                    "title": title,
                    "artist": artist,
                    "isrc": isrc,
                    "duration_sec": duration_sec,
                    "source": "youtube",
                    "youtube_id": youtube_id,
                    "safe_title": safe_title,       # for filenames
                    "safe_artist": safe_artist      # for filenames
                })

        return tracks