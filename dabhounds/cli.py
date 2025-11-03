# dabhounds/cli.py

import argparse
import sys
import os
from datetime import datetime
from pathlib import Path
import subprocess
import requests

from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials

from dabhounds.core.spotify import SpotifyFetcher
from dabhounds.core.youtube_parser_v3 import YouTubeParserV3
from dabhounds.core.dab import match_track
from dabhounds.core.library import create_library, add_tracks_to_library, library_exists
from dabhounds.core.report import generate_report, load_report, append_tracks_to_report
from dabhounds.core.auth import login, ensure_logged_in, load_config, save_config
from dabhounds.core.spotify_auth import get_spotify_client, spotify_logout

# Load configuration
cfg = load_config()

ASCII_ART = r"""
  _____          ____  _    _                       _         
 |  __ \   /\   |  _ \| |  | |                     | |        
 | |  | | /  \  | |_) | |__| | ___  _   _ _ __   __| |___     
 | |  | |/ /\ \ |  _ <|  __  |/ _ \| | | | '_ \ / _` / __|    
 | |__| / ____ \| |_) | |  | | (_) | |_| | | | | (_| \__ \    
 |_____/_/    \_\____/|_|  |_|\___/ \__,_|_| |_|\__,_|___/    
"""

def show_main_menu():
    print(ASCII_ART)
    print("""
Developed By: sherlockholmesat221b
Special Thanks To: superadmin0, uimaxbai, joehacks, Squid.WTF

Available Commands:

  dabhounds <link> [--mode strict|lenient|manual]
      → Convert a Spotify or YouTube link into a DAB library

  dabhounds --login
      → Log in to your DAB account

  dabhounds --spotify-login
      → Authenticate with Spotify via OAuth

  dabhounds --logout
      → Log out of DAB and Spotify

  dabhounds --threshold <0-100>
      → Override fuzzy match threshold

  dabhounds --version
      → Show DABHounds version

  dabhounds --update
      → Check for updates

  dabhounds --credits
      → Show credits
""")

def show_credits():
    print(ASCII_ART)
    print("""
DABHounds — "The hound is on the scent."

Visit: https://dabmusic.xyz

Developed by: sherlockholmesat221b
Special Thanks To: superadmin0, uimaxbai, joehacks, Squid.WTF
""")

def load_version():
    try:
        with open("VERSION", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "0.0.0"

VERSION_URL = "https://raw.githubusercontent.com/sherlockholmesat221b/DABHounds/main/VERSION"

def check_latest_version(local_version):
    try:
        r = requests.get(VERSION_URL, timeout=5)
        r.raise_for_status()
        remote_version = r.text.strip()
        if remote_version != local_version:
            print(f"[DABHound] New version available: {remote_version} (current: {local_version}). Run --update to update.")
        else:
            print(f"[DABHound] You are running the latest version ({local_version}).")
    except Exception as e:
        print(f"[DABHound] Could not check for updates: {e}")

def perform_update():
    try:
        print("[DABHound] Updating via pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "dabhounds"])
        print("[DABHound] Update complete. Please restart the tool.")
    except subprocess.CalledProcessError as e:
        print(f"[DABHound] Update failed: {e}")

def is_spotify_url(url: str) -> bool:
    return "open.spotify.com" in url

def is_youtube_url(url: str) -> bool:
    return "youtube.com" in url or "youtu.be" in url

def logout():
    cfg = load_config()
    for key in ["DAB_AUTH_TOKEN", "DAB_EMAIL", "DAB_PASSWORD", "SPOTIFY_TOKEN"]:
        cfg.pop(key, None)
    save_config(cfg)
    cache_path = ".cache-dabhound"
    if os.path.exists(cache_path):
        os.remove(cache_path)
    spotify_logout()
    print("[DABHound] Logged out and cleared credentials.")

def main():
    parser = argparse.ArgumentParser(description="DABHounds: Convert Spotify or YouTube to DAB libraries")
    parser.add_argument("link", nargs="?", help="Spotify/YouTube/ISRC input")
    parser.add_argument("--mode", choices=["strict","lenient","manual"], default=None)
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--login", action="store_true")
    parser.add_argument("--logout", action="store_true")
    parser.add_argument("--spotify-login", action="store_true")
    parser.add_argument("--credits", action="store_true")
    parser.add_argument("--threshold", type=int, help="Override fuzzy threshold 0-100")
    args = parser.parse_args()

    fuzzy_threshold = args.threshold or cfg.get("FUZZY_THRESHOLD", 80)

    if len(sys.argv) == 1:
        show_main_menu()
        sys.exit(0)

    if args.credits:
        show_credits()
        sys.exit(0)

    if args.version:
        print(f"DABHounds v{load_version()}")
        check_latest_version(load_version())
        sys.exit(0)

    if args.update:
        confirm = input("This will upgrade DABHounds via pip. Continue? (y/N): ").strip().lower()
        if confirm == "y":
            perform_update()
        sys.exit(0)

    if args.logout:
        logout()
        sys.exit(0)

    if args.login:
        email = input("Email: ").strip()
        password = input("Password: ").strip()
        login(email, password)
        sys.exit(0)

    if args.spotify_login:
        sp = get_spotify_client()
        print(f"[DABHound] Spotify login successful as: {sp.current_user()['display_name']}")
        sys.exit(0)

    if not args.link:
        parser.print_help()
        sys.exit(1)

    # strip input URL and remove tracking parameters
    link = args.link.strip()
    
    # Remove ?si= parameter from Spotify links
    if "?si=" in link:
        link = link.split("?si=")[0]
    
    # Remove &si= parameter from Spotify links
    if "&si=" in link:
        link = link.split("&si=")[0]
    
    print(f"[DABHound] Input URL: {link}")
    match_mode = args.mode or cfg.get("MATCH_MODE", "lenient")
    token = ensure_logged_in()

    # === TRACK FETCHING ===
    tracks = []
    if is_spotify_url(link):
        print("[DABHound] Detected Spotify link")
        try:
            public_sp = Spotify(auth_manager=SpotifyClientCredentials(
                client_id=cfg.get("SPOTIPY_CLIENT_ID"),
                client_secret=cfg.get("SPOTIPY_CLIENT_SECRET")
            ))
            fetcher = SpotifyFetcher(public_sp)
            tracks = fetcher.extract_tracks(link)
        except Exception:
            print("[DABHound] Private/restricted playlist. Logging in...")
            sp = get_spotify_client()
            fetcher = SpotifyFetcher(sp)
            tracks = fetcher.extract_tracks(link)
        for t in tracks:
            t["source_url"] = link
    elif is_youtube_url(link):
        print("[DABHound] Detected YouTube link")
        parser_y = YouTubeParserV3(cfg.get("YOUTUBE", {}))
        tracks = parser_y.parse(link)
        for t in tracks:
            if "safe_title" in t:
                t["title"] = t["safe_title"]
            if "safe_artist" in t and t["safe_artist"]:
                t["artist"] = t["safe_artist"]
            if not t.get("artist") or "youtube" in t["artist"].lower():
                if " - " in t["title"]:
                    parts = t["title"].split(" - ", 1)
                    t["artist"], t["title"] = parts[0], parts[1]
            t["source_url"] = link
    else:
        print("[DABHound] Only Spotify and YouTube are supported")
        sys.exit(1)

    if not tracks:
        print("[DABHound] No tracks found")
        sys.exit(1)

    print(f"[DABHound] Found {len(tracks)} tracks")

    # === SYNC DETECTION & TRACK PROCESSING ===
    existing_report = load_report(link)
    append_mode = False
    existing_ids = set()
    
    if existing_report:
        library_id = existing_report.get("library_id")
    
        if library_id and not library_exists(library_id):
            print("[DABHound] Previous DAB library no longer exists. Cleaning up old report...")

            # delete old report file(s)
            from dabhounds.core.report import delete_report
            delete_report(link)
    
            # reset state - treat as new conversion
            existing_report = None
            tracks_to_process = tracks[:]
            print("[DABHound] Starting fresh conversion; processing all tracks.")
        else:
            # Library exists, check for duplicates
            for t in existing_report.get("tracks", []):
                if "spotify_id" in t:
                    existing_ids.add(t["spotify_id"])
                elif "yt_id" in t:
                    existing_ids.add(t["yt_id"])
                elif "isrc" in t and t["isrc"]:
                    existing_ids.add(t["isrc"])
                else:
                    existing_ids.add(f"{t['artist']} - {t['title']}")
    
            tracks_to_process = []
            for t in tracks:
                track_id = t.get("spotify_id") or t.get("yt_id") or t.get("isrc") or f"{t['artist']} - {t['title']}"
                if track_id not in existing_ids:
                    tracks_to_process.append(t)
    
            skipped_count = len(tracks) - len(tracks_to_process)
            if skipped_count:
                print(f"[DABHound] {skipped_count} tracks already present in report; processing {len(tracks_to_process)} new tracks.")
            else:
                print("[DABHound] No previously-synced tracks found; processing all tracks.")
    
            append_mode = True
    else:
        tracks_to_process = tracks[:]
        print("[DABHound] No previously-synced tracks; processing all tracks.")

    # === MATCHING TRACKS ===  
    matched_tracks = []  
    match_results = []  
    for idx, track in enumerate(tracks_to_process, start=1):  
        print(f"\n[DABHound] Matching ({idx}/{len(tracks_to_process)}): {track.get('artist','')} - {track.get('title','')}")  
        result = match_track(track, match_mode, token, fuzzy_threshold)  
        match_results.append(result or {})  

        if result:  
            print(f"[DABHound] Match found: {result.get('artist','')} - {result.get('title','')} (DAB ID: {result.get('id')})")  
            matched_tracks.append({  
                "artist": result.get("artist", track.get("artist")),  
                "title": result.get("title", track.get("title")),  
                "isrc": track.get("isrc"),  
                "match_status": "FOUND",  
                "dab_track_id": result.get("id"),  
                "source_url": track.get("source_url"),  
                "full_track": result  # <--- attach the full DAB track dict  
            })  
        else:  
            print(f"[DABHound] No match found for: {track.get('artist','')} - {track.get('title','')}")  
            matched_tracks.append({  
                "artist": track.get("artist"),  
                "title": track.get("title"),  
                "isrc": track.get("isrc"),  
                "match_status": "NOT_FOUND",  
                "dab_track_id": None,  
                "source_url": track.get("source_url"),  
            })

    # === LIBRARY CREATION / UPDATE ===
    library_id = "(none)"
    library_name = "(none)"

    if matched_tracks:
        if append_mode and existing_report:
            library_id = existing_report.get("library_id", "(none)")
            library_name = existing_report.get("library_name", f"DABHounds {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            print(f"[DABHound] Adding new tracks to existing library: {library_name}")
        else:
            library_name = f"DABHounds {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            print(f"[DABHound] Creating new library: {library_name}")
            library_id = create_library(library_name, description="Created by DABHounds", is_public=True)
            print(f"[DABHound] Library created. ID: {library_id}")

        if matched_tracks:
            add_tracks_to_library(library_id, matched_tracks)
            print(f"[DABHound] Library updated! Link: https://dabmusic.xyz/shared/library/{library_id}")
    else:
        if append_mode and existing_report:
            library_id = existing_report.get("library_id", "(none)")
            library_name = existing_report.get("library_name", "(none)")
            print("[DABHound] No new matches found to append; using existing library info.")
        else:
            print("[DABHound] No tracks matched; skipping library creation.")

    # === REPORT WRITING (TXT + JSON) ===
    if append_mode and existing_report:
        append_tracks_to_report(
            link,
            tracks_to_process,
            library_id=library_id,
            library_name=library_name,
            matching_mode=match_mode
        )
    else:
        generate_report(
            tracks_to_process,
            matched_tracks,
            match_results,
            match_mode,
            library_name,
            library_id,
            source_url=link
        )

    print(f"[DABHound] Conversion complete. Reports written for {len(matched_tracks)} tracks.")

if __name__ == "__main__":
    main()