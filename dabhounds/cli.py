# dabhounds/cli.py   
  
import argparse  
import json  
import sys  
import os  
from datetime import datetime  
import requests  
import shutil  
import tempfile  
import zipfile  
from pathlib import Path  
import subprocess  
  
from spotipy import Spotify  
from spotipy.oauth2 import SpotifyClientCredentials  
from dabhounds.core.spotify import SpotifyFetcher  
from dabhounds.core.youtube_parser_v3 import YouTubeParserV3  
from dabhounds.core.dab import match_track  
from dabhounds.core.library import create_library, add_tracks_to_library  
from dabhounds.core.report import find_reports_for_source, load_source_ids_from_report, append_to_report, REPORT_DIR
from dabhounds.core.auth import login, ensure_logged_in, load_config, save_config  
from dabhounds.core.spotify_auth import get_spotify_client  
  
# Load user config (will auto-create ~/.dabhound/config.json if missing)  
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
      → Override fuzzy match threshold for linient conversion (default: from config.json)  
  
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
- superadmin0 (Creator of DABMusic) — for building and maintaining DABMusic, the rock-solid foundation for this tool.  
- uimaxbai (Contributor/Developer at DABMusic) — for guiding the development of this tool and testing it firsthand.  
- joehacks (Contributor/Developer at DABMusic) — for testing the tool firsthand.  
- Squid.WTF — for graciously allowing the use of their API.  
""")  
  
  
def load_version():  
    try:  
        with open("VERSION", "r") as f:  
            return f.read().strip()  
    except FileNotFoundError:  
        return "0.0.0"  
  
  
  
VERSION_URL = "https://raw.githubusercontent.com/sherlockholmesat221b/DABHounds/main/VERSION"  
REPO_ZIP_URL = "https://github.com/sherlockholmesat221b/DABHounds/archive/refs/heads/main.zip"  
  
def check_latest_version(local_version):  
    try:  
        r = requests.get(VERSION_URL, timeout=5)  
        r.raise_for_status()  
        remote_version = r.text.strip()  
        if remote_version != local_version:  
            print(f"[DABHound] New version available: {remote_version} (current: {local_version}). Run --update to update.")  
            return remote_version  
        else:  
            print(f"[DABHound] You are running the latest version ({local_version}).")  
            return None  
    except Exception as e:  
        print(f"[DABHound] Could not check for updates: {e}")  
        return None  
  
def perform_update():  
    try:  
        print("[DABHound] Updating via pip...")  
        # Use the current Python executable to upgrade the package  
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "dabhounds"])  
        print("[DABHound] Update complete. Please restart the tool.")  
    except subprocess.CalledProcessError as e:  
        print(f"[DABHound] Update failed: {e}")  
        print("[DABHound] Make sure you have internet access and pip installed.")  
   
def is_spotify_url(url: str) -> bool:  
    return "open.spotify.com" in url  
  
def is_youtube_url(url: str) -> bool:  
    return "youtube.com" in url or "youtu.be" in url  
  
def logout():  
    config = load_config()  
    for key in [  
        "DAB_AUTH_TOKEN", "DAB_EMAIL", "DAB_PASSWORD",  
        "SPOTIFY_TOKEN"  
    ]:  
        config.pop(key, None)  
  
    save_config(config)  
  
    cache_path = ".cache-dabhound"  
    if os.path.exists(cache_path):  
        os.remove(cache_path)  
  
    print("[DABHound] Logged out and cleared all credentials.")  
  
def main():  
    parser = argparse.ArgumentParser(  
        description="DABHounds: Convert Spotify or YouTube to DAB libraries",  
        usage="python dabhounds <link> [--mode strict|lenient|manual]"  
    )  
    parser.add_argument("link", nargs="?", help="Spotify/YouTube/ISRC input (Spotify & YouTube supported)")  
    parser.add_argument("--mode", choices=["strict", "lenient", "manual"], default=None, help="Matching mode to use")  
    parser.add_argument("--version", action="store_true", help="Show current version")  
    parser.add_argument("--update", action="store_true", help="Check for updates (not implemented)")  
    parser.add_argument("--login", action="store_true", help="Log in to DAB")  
    parser.add_argument("--logout", action="store_true", help="Log out of DAB and Spotify")  
    parser.add_argument("--spotify-login", action="store_true", help="Authenticate with Spotify via OAuth")  
    parser.add_argument("--credits", action="store_true", help="Show tool credits and acknowledgements")  
    parser.add_argument(  
        "--threshold",  
        type=int,  
        help="Override fuzzy search match threshold percentage (0-100)."  
    )  
  
    args = parser.parse_args()  
    config = load_config()  
    version = load_version()  
    fuzzy_threshold = args.threshold or config.get("FUZZY_THRESHOLD", 80)  
  
    # === No args → Show menu ===  
    if len(sys.argv) == 1:  
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
        else:  
            print("[DABHound] Update cancelled.")  
        sys.exit(0)  
  
  
    if args.logout:  
        from dabhounds.core.spotify_auth import spotify_logout  
        logout()  
        spotify_logout()  
        sys.exit(0)  
  
    if args.login:  
        email = input("Email: ").strip()  
        password = input("Password: ").strip()  
        login(email, password)  
        sys.exit(0)  
  
    if args.spotify_login:  
        sp = get_spotify_client()  
        user = sp.current_user()  
        print(f"[DABHound] Spotify login successful as: {user['display_name']}")  
        sys.exit(0)  
  
    if not args.link:  
        parser.print_help()  
        sys.exit(1)  
  
    token = ensure_logged_in()  
    match_mode = args.mode or config.get("MATCH_MODE", "lenient")  
  
    # ==== TRACK FETCHING PHASE ====  
    if is_spotify_url(args.link):  
        print("[DABHound] Detected Spotify link.")  
  
        try:  
            public_sp = Spotify(  
                auth_manager=SpotifyClientCredentials(  
                    client_id=config.get("SPOTIPY_CLIENT_ID"),  
                    client_secret=config.get("SPOTIPY_CLIENT_SECRET")  
                )  
            )  
            fetcher = SpotifyFetcher(sp_client=public_sp)  
            print("[DABHound] Fetching Spotify tracks without login...")  
            tracks = fetcher.extract_tracks(args.link)  
  
        except Exception as e:  
            if "401" in str(e) or "403" in str(e) or "Not found" in str(e):  
                print("[DABHound] Playlist is private or restricted, logging in to Spotify...")  
                sp = get_spotify_client()  
                fetcher = SpotifyFetcher(sp_client=sp)  
                tracks = fetcher.extract_tracks(args.link)  
            else:  
                raise  
  
    elif is_youtube_url(args.link):  
        print("[DABHound] Detected YouTube link.")  
        parser = YouTubeParserV3(config=config.get("YOUTUBE", {}))  
        print("[DABHound] Fetching YouTube metadata...")  
        tracks = parser.parse(args.link)  
  
        for t in tracks:  
            if "safe_title" in t:  
                t["title"] = t["safe_title"]  
            if "safe_artist" in t and t["safe_artist"]:  
                t["artist"] = t["safe_artist"]  
            if not t.get("artist") or "youtube" in t["artist"].lower():  
                if " - " in t["title"]:  
                    parts = t["title"].split(" - ", 1)  
                    t["artist"], t["title"] = parts[0], parts[1]  
  
    else:  
        print("[DABHound] Only Spotify and YouTube links are supported right now.")  
        sys.exit(1)  
  
    if not tracks:  
        print("[DABHound] No tracks found in input.")  
        sys.exit(1)  
  
    print(f"[DABHound] Found {len(tracks)} tracks.")

    # === Sync detection: look for existing report(s) with this source URL ===
    matching_reports = find_reports_for_source(args.link)
    if matching_reports:
        # pick the most recent report
        report_path = matching_reports[0]
        print(f"[DABHound] Found existing report for this source: {report_path.name}")
        existing_source_ids = load_source_ids_from_report(report_path)
        # Filter out tracks already present in the report
        tracks_to_process = [t for t in tracks if (t.get("source_id") and t.get("source_id") not in existing_source_ids)]
        skipped = len(tracks) - len(tracks_to_process)
        if skipped:
            print(f"[DABHound] {skipped} tracks already present in report; will only process {len(tracks_to_process)} new tracks.")
        else:
            print("[DABHound] No previously-synced tracks found in report; processing all tracks.")
        append_mode = True
    else:
        report_path = None
        tracks_to_process = tracks[:]  # process all
        append_mode = False
  
    # ==== MATCHING PHASE ====  
    match_results = []
    matched_tracks = []
    total_tracks = len(tracks_to_process)

    if total_tracks == 0:
        print("[DABHound] No new tracks to sync. Exiting.")
        sys.exit(0)

    for idx, track in enumerate(tracks_to_process, start=1):
        print(f"\n[DABHound] Matching ({idx}/{total_tracks}): {track.get('artist','')} - {track.get('title','')}")
        result = match_track(track, match_mode, token, fuzzy_threshold)
        match_results.append(result)
        if result:
            print(f"[DABHound] Matched ({idx}/{total_tracks}): {result.get('artist','')} - {result.get('title','')} (DAB ID: {result.get('id')})")
            matched_tracks.append(result)
        else:
            print(f"[DABHound] No match found ({idx}/{total_tracks}).")
  
    # ==== LIBRARY CREATION PHASE ====
    if matched_tracks:
        # If we found an existing report and have append_mode, re-use the existing library id when possible.
        if append_mode and report_path:
            # Attempt to parse the existing report for the library id line
            existing_library_id = None
            try:
                with report_path.open("r", encoding="utf-8") as rf:
                    for line in rf:
                        if line.strip().startswith("DAB Library ID:"):
                            existing_library_id = line.split("DAB Library ID:",1)[1].strip()
                            break
            except Exception:
                existing_library_id = None

            if existing_library_id and existing_library_id != "(none)":
                library_id = existing_library_id
                library_name = report_path.stem.replace("report_", "").replace("_", " ")
                print(f"\n[DABHound] Re-using existing DAB library ID from report: {library_id}")
            else:
                library_name = f"DABHounds {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                print(f"\n[DABHound] Creating DAB library: {library_name}")
                library_id = create_library(library_name, description="Created by DABHounds (sync)", is_public=True)
        else:
            library_name = f"DABHounds {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            print(f"\n[DABHound] Creating DAB library: {library_name}")
            library_id = create_library(library_name, description="Created by DABHounds", is_public=True)

        add_tracks_to_library(library_id, matched_tracks)
        print(f"[DABHound] Library updated! Link: https://dabmusic.xyz/shared/library/{library_id}")
    else:
        # no matched tracks in this run
        if append_mode:
            print("[DABHound] No new matches found to append.")
        else:
            library_id = "(none)"
            print("[DABHound] No tracks matched. Skipping library creation.")
  
    # Write or append report
    if append_mode and report_path:
        # append the newly-processed tracks to existing report
        append_to_report(report_path, tracks_to_process, match_results, library_id, match_mode)
    else:
        # create a new report file (this will overwrite if same name exists)
        generate_report(tracks_to_process, matched_tracks, match_results, match_mode, library_name, library_id, args.link)
  
if __name__ == "__main__":  
    main()