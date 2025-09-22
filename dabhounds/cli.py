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
from dabhounds.core.library import create_library, add_tracks_to_library
from dabhounds.core.report import generate_report, load_report, append_tracks_to_report
from dabhounds.core.auth import login, ensure_logged_in, load_config, save_config
from dabhounds.core.spotify_auth import get_spotify_client, spotify_logout

config = load_config()
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
Developed By: sherlockholmesat221b (sherlockholmesat221b@proton.me)
Special Thanks To: superadmin0, uimaxbai, joehacks, and Squid.WTF.

Available Commands:

  dabhounds <link> [--mode strict|lenient|manual]
      → Convert a Spotify or YouTube link into a DAB library

  dabhounds --login
      → Log in to your DAB account

  dabhounds --spotify-login
      → Authenticate with Spotify via OAuth (for private playlists)

  dabhounds --logout
      → Log out of DAB and Spotify

  dabhounds --threshold <0-100>
      → Override fuzzy match threshold for lenient conversion

  dabhounds --version
      → Show DABHounds version

  dabhounds --update
      → Check for updates

  dabhounds --credits
      → View credits and acknowledgements
""")

def show_credits():
    print(ASCII_ART)
    print("""
DABHounds — “The hound is on the scent.”
A vigilant tracker that sniffs out your music across DAB.
Inspired by the keen nose of a bloodhound and the mysteries of Baker Street.

Visit: https://dabmusic.xyz

Developed by:
sherlockholmesat221b (sherlockholmesat221b@proton.me)

Special Thanks To:
- superadmin0 (Creator of DABMusic)
- uimaxbai (Contributor/Developer at DABMusic)
- joehacks (Contributor/Developer at DABMusic)
- Squid.WTF
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
    print("[DABHound] Logged out and cleared all credentials.")

def track_source_id(track: dict) -> str:
    return track.get("spotify_id") or track.get("youtube_id") or track.get("isrc") or track.get("title")

def main():
    parser = argparse.ArgumentParser(description="DABHounds: Convert Spotify or YouTube to DAB libraries")
    parser.add_argument("link", nargs="?", help="Spotify/YouTube/ISRC input (Spotify & YouTube supported)")
    parser.add_argument("--mode", choices=["strict","lenient","manual"], default=None)
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--login", action="store_true")
    parser.add_argument("--logout", action="store_true")
    parser.add_argument("--spotify-login", action="store_true")
    parser.add_argument("--credits", action="store_true")
    parser.add_argument("--threshold", type=int, help="Override fuzzy threshold 0-100")

    args = parser.parse_args()
    cfg = load_config()
    version = load_version()
    fuzzy_threshold = args.threshold or cfg.get("FUZZY_THRESHOLD", 80)

    if len(sys.argv)==1:
        show_main_menu()
        sys.exit(0)

    if args.credits:
        show_credits()
        sys.exit(0)
    if args.version:
        print(f"DABHounds v{version}")
        check_latest_version(version)
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
        login(email,password)
        sys.exit(0)
    if args.spotify_login:
        sp = get_spotify_client()
        print(f"[DABHound] Spotify login successful as: {sp.current_user()['display_name']}")
        sys.exit(0)
    if not args.link:
        parser.print_help()
        sys.exit(1)

    token = ensure_logged_in()
    match_mode = args.mode or cfg.get("MATCH_MODE","lenient")

    # === TRACK FETCHING ===
    if is_spotify_url(args.link):
        print("[DABHound] Detected Spotify link")
        try:
            public_sp = Spotify(auth_manager=SpotifyClientCredentials(client_id=cfg.get("SPOTIPY_CLIENT_ID"), client_secret=cfg.get("SPOTIPY_CLIENT_SECRET")))
            fetcher = SpotifyFetcher(public_sp)
            tracks = fetcher.extract_tracks(args.link)
        except Exception as e:
            print("[DABHound] Private/restricted playlist. Logging in...")
            sp = get_spotify_client()
            fetcher = SpotifyFetcher(sp)
            tracks = fetcher.extract_tracks(args.link)
    elif is_youtube_url(args.link):
        print("[DABHound] Detected YouTube link")
        parser_y = YouTubeParserV3(cfg.get("YOUTUBE",{}))
        tracks = parser_y.parse(args.link)
        for t in tracks:
            if "safe_title" in t: t["title"]=t["safe_title"]
            if "safe_artist" in t and t["safe_artist"]: t["artist"]=t["safe_artist"]
            if not t.get("artist") or "youtube" in t["artist"].lower():
                if " - " in t["title"]:
                    parts = t["title"].split(" - ",1)
                    t["artist"],t["title"]=parts[0],parts[1]
    else:
        print("[DABHound] Only Spotify and YouTube supported")
        sys.exit(1)
    if not tracks:
        print("[DABHound] No tracks found")
        sys.exit(1)
    print(f"[DABHound] Found {len(tracks)} tracks")

    # === REPORT/DEEP SYNC ===
    existing_report = load_report(args.link)
    if existing_report:
        existing_ids = {t["source_id"] for t in existing_report.get("tracks",[])}
        tracks_to_process = [t for t in tracks if track_source_id(t) not in existing_ids]
        append_mode = True
        if not tracks_to_process:
            print("[DABHound] No new tracks to sync. Exiting.")
            sys.exit(0)
        print(f"[DABHound] {len(tracks_to_process)} new tracks to process")
    else:
        tracks_to_process = tracks[:]
        append_mode = False

    # === MATCHING ===
    match_results=[]
    matched_tracks=[]
    for idx, track in enumerate(tracks_to_process, start=1):
        print(f"[DABHound] Matching ({idx}/{len(tracks_to_process)}): {track.get('artist')} - {track.get('title')}")
        res = match_track(track, match_mode, token, fuzzy_threshold)
        match_results.append(res)
        if res:
            matched_tracks.append(res)
            print(f"[DABHound] Matched: {res.get('artist')} - {res.get('title')} (ID: {res.get('id')})")
        else:
            print(f"[DABHound] No match found")

    # === LIBRARY CREATION/UPDATE ===
    if matched_tracks:
        if append_mode and existing_report:
            library_id = existing_report.get("library_id")
            library_name = existing_report.get("library_name")
            print(f"[DABHound] Adding new tracks to existing library: {library_name}")
        else:
            library_name=f"DABHounds {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            library_id = create_library(library_name, description="Created by DABHounds", is_public=True)
            print(f"[DABHound] Created new library: {library_name}")
        add_tracks_to_library(library_id, matched_tracks)
        print(f"[DABHound] Library updated! Link: https://dabmusic.xyz/shared/library/{library_id}")
    else:
        library_id = existing_report.get("library_id") if existing_report else "(none)"
        print("[DABHound] No tracks matched.")

    # === REPORT GENERATION ===
    report_data = [{
        "artist": t.get("artist"),
        "title": t.get("title"),
        "isrc": t.get("isrc"),
        "source_id": track_source_id(t),
        "match_status": "FOUND" if m else "NOT FOUND",
        "dab_track": m
    } for t,m in zip(tracks_to_process, match_results)]

    if append_mode:
        append_tracks_to_report(args.link, report_data, library_id=library_id, library_name=library_name)
    else:
        generate_report(tracks_to_process, matched_tracks, match_results, match_mode, library_name, library_id, source_url=args.link)

if __name__=="__main__":
    main()