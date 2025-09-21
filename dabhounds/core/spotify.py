# dabhounds/core/spotify.py

from typing import List, Dict
import spotipy

class SpotifyFetcher:
    def __init__(self, sp_client):
        self.sp = sp_client  # Pass either public or OAuth client

    @staticmethod
    def detect_spotify_type(url: str) -> str:
        if "playlist" in url:
            return "playlist"
        elif "album" in url:
            return "album"
        elif "track" in url:
            return "track"
        else:
            raise ValueError("[DABHound] Unsupported Spotify URL format.")

    def get_playlist_tracks(self, playlist_url: str) -> List[Dict]:
        playlist_id = playlist_url.split("/")[-1].split("?")[0]
        results = self.sp.playlist_tracks(playlist_id)
        tracks = []

        while results:
            for item in results["items"]:
                track = item["track"]
                if not track:
                    continue
                tracks.append({
                    "title": track["name"],
                    "artist": ", ".join([a["name"] for a in track["artists"]]),
                    "isrc": track["external_ids"].get("isrc"),
                    "duration_ms": track["duration_ms"],
                    "spotify_id": track["id"]
                })
            if results["next"]:
                results = self.sp.next(results)
            else:
                break

        return tracks

    def get_album_tracks(self, album_url: str) -> List[Dict]:
        album_id = album_url.split("/")[-1].split("?")[0]
        results = self.sp.album_tracks(album_id)
        tracks = []

        for item in results["items"]:
            track_info = self.sp.track(item["id"])
            tracks.append({
                "title": item["name"],
                "artist": ", ".join([a["name"] for a in item["artists"]]),
                "isrc": track_info.get("external_ids", {}).get("isrc"),
                "duration_ms": item["duration_ms"],
                "spotify_id": item["id"]
            })

        return tracks

    def get_track(self, track_url: str) -> List[Dict]:
            track_id = track_url.split("/")[-1].split("?")[0]
            track = self.sp.track(track_id)
            return [{
                "title": track["name"],
                "artist": ", ".join([a["name"] for a in track["artists"]]),
                "isrc": track["external_ids"].get("isrc"),
                "duration_ms": track["duration_ms"],
                "spotify_id": track["id"]
            }]
    
    def extract_tracks(self, url: str) -> List[Dict]:
        kind = self.detect_spotify_type(url)
    
        try:
            # First try with whatever client is currently set
            if kind == "playlist":
                return self.get_playlist_tracks(url)
            elif kind == "album":
                return self.get_album_tracks(url)
            elif kind == "track":
                return self.get_track(url)
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 404:
                from dabhounds.core.spotify_auth import get_spotify_client
                print("[DABHound] Resource not found with public client, retrying with OAuth...")
                self.sp = get_spotify_client()  # swap to OAuth client
    
                try:
                    if kind == "playlist":
                        return self.get_playlist_tracks(url)
                    elif kind == "album":
                        return self.get_album_tracks(url)
                    elif kind == "track":
                        return self.get_track(url)
                except spotipy.exceptions.SpotifyException as e2:
                    if e2.http_status == 404:
                        print("[DABHound] Playlist could not be accessed via the API. "
                              "It may be an editorial/restricted playlist.")
                        return []
                    else:
                        raise
            else:
                raise