# dabhounds/core/spotify_auth.py 

import os  
import json  
from spotipy import Spotify  
from spotipy.oauth2 import SpotifyOAuth  
  
CONFIG_PATH = "config.json"  
CACHE_PATH = ".cache-dabhound"  
SPOTIFY_SCOPES = "playlist-read-private playlist-read-collaborative"  
  
def load_config(path=CONFIG_PATH) -> dict:  
    if not os.path.isfile(path):  
        return {}  
    try:  
        with open(path, "r") as f:  
            return json.load(f)  
    except Exception:  
        return {}  
  
def save_config(config: dict, path=CONFIG_PATH):  
    try:  
        with open(path, "w") as f:  
            json.dump(config, f, indent=4)  
    except Exception as e:  
        print(f"[DABHound] Failed to save config: {e}")  
  
def get_spotify_auth_manager():  
    config = load_config()  
  
    # Hardcoded Spotify credentials
    client_id = "440ca0fe7cc54e91af9b50972e783552"
    client_secret = "45737683ac27405580188fc7b009ea06"
    redirect_uri = "http://127.0.0.1:8888/callback"
  
    auth_manager = SpotifyOAuth(  
        client_id=client_id,  
        client_secret=client_secret,  
        redirect_uri=redirect_uri,  
        scope=SPOTIFY_SCOPES,  
        open_browser=False,  
        cache_path=CACHE_PATH,  
        show_dialog=False  
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
        os.remove(".cache-dabhound")  
        print("[DABHound] Logged out from Spotify.")  
    except FileNotFoundError:  
        print("[DABHound] No Spotify session found.")