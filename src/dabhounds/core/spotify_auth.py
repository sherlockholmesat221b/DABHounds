# dabhounds/core/spotify_auth.py

import os
import json
from pathlib import Path
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

CONFIG_DIR = Path.home() / ".dabhound"
CONFIG_FILE = CONFIG_DIR / "config.json"
CACHE_FILE = CONFIG_DIR / ".cache-dabhound"
SPOTIFY_SCOPES = "playlist-read-private playlist-read-collaborative"
HOWTO_URL = "https://rentry.co/dabhounds-spotify-setup"

def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(config: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with CONFIG_FILE.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"[DABHound] Failed to save config: {e}")

def ensure_spotify_credentials(config: dict) -> dict:
    client_id = config.get("SPOTIFY_CLIENT_ID")
    client_secret = config.get("SPOTIFY_CLIENT_SECRET")
    redirect_uri = config.get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")

    if not client_id or not client_secret:
        print("[DABHound] Spotify credentials not found.")
        print(f"[DABHound] See setup guide: {HOWTO_URL}")
        print("Enter your Spotify app credentials (from https://developer.spotify.com/dashboard):")

        client_id = input("  SPOTIFY_CLIENT_ID: ").strip()
        client_secret = input("  SPOTIFY_CLIENT_SECRET: ").strip()
        redirect_uri = input(f"  SPOTIFY_REDIRECT_URI [{redirect_uri}]: ").strip() or redirect_uri

        config["SPOTIFY_CLIENT_ID"] = client_id
        config["SPOTIFY_CLIENT_SECRET"] = client_secret
        config["SPOTIFY_REDIRECT_URI"] = redirect_uri
        save_config(config)

    return config

def get_spotify_auth_manager() -> SpotifyOAuth:
    config = load_config()
    config = ensure_spotify_credentials(config)

    auth_manager = SpotifyOAuth(
        client_id=config["SPOTIFY_CLIENT_ID"],
        client_secret=config["SPOTIFY_CLIENT_SECRET"],
        redirect_uri=config.get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback"),
        scope=SPOTIFY_SCOPES,
        open_browser=False,
        cache_path=str(CACHE_FILE),
        show_dialog=False,
    )

    try:
        token_info = auth_manager.get_cached_token()
        if token_info is None or auth_manager.is_token_expired(token_info):
            token_info = auth_manager.get_access_token(as_dict=True)
        if token_info:
            config["SPOTIFY_TOKEN"] = token_info
            save_config(config)
    except Exception as e:
        print(f"[DABHound] Failed to authenticate with Spotify: {e}")
        raise

    return auth_manager

def get_spotify_client() -> Spotify:
    auth_manager = get_spotify_auth_manager()
    return Spotify(auth_manager=auth_manager)

def spotify_logout():
    try:
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()
        print("[DABHound] Logged out from Spotify.")
    except Exception:
        print("[DABHound] No Spotify session found.")