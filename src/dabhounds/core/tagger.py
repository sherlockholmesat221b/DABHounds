# dabhounds/core/tagger.py

import os
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, ID3NoHeaderError, APIC, USLT
from dabhounds.core.auth import load_config, get_authenticated_session


# -------------------- Lyrics Fetcher --------------------
def get_lyrics(title: str, artist: str) -> tuple[str, bool] | tuple[None, None]:
    """
    Fetch lyrics for a song from the DAB API.
    Returns (lyrics_text, unsynced: bool).
    If lyrics not found, returns (None, None).
    """
    if not title or not artist:
        return None, None

    config = load_config()
    base_url = config.get("DAB_API_BASE", "https://dab.yeet.su/api")

    try:
        session = get_authenticated_session()
        resp = session.get(
            f"{base_url}/lyrics",
            params={"title": title, "artist": artist},
            timeout=10
        )

        if resp.status_code != 200:
            return None, None

        data = resp.json()
        lyrics = data.get("lyrics", "").strip()
        unsynced = data.get("unsynced", True)

        if not lyrics:
            return None, None

        return lyrics, unsynced

    except Exception as e:
        if config.get("debug", False):
            print(f"[tagger] Failed to fetch lyrics: {e}")
        return None, None


# -------------------- Helpers --------------------
def save_lrc(file_path: str, lyrics: str):
    """Save synced lyrics as .lrc file alongside audio."""
    base, _ = os.path.splitext(file_path)
    lrc_path = base + ".lrc"
    with open(lrc_path, "w", encoding="utf-8") as f:
        f.write(lyrics)
    config = load_config()
    if config.get("debug", False):
        print(f"[tagger] Saved synced lyrics to {lrc_path}")


# -------------------- Main Tagger --------------------
def tag_audio(file_path: str, metadata: dict, cover_path: str = None):
    """
    Tags metadata, cover art, and lyrics into MP3 or FLAC.
    Any other format is skipped.
    """
    config = load_config()
    dl_cfg = config.get("download", {})

    if not dl_cfg.get("use_metadata_tagging", True) or not os.path.exists(file_path):
        return False

    title  = metadata.get("title", "")
    artist = metadata.get("artist", "")

    lyrics, unsynced = get_lyrics(title, artist) if dl_cfg.get("get_lyrics", True) else (None, None)
    ext = os.path.splitext(file_path)[-1].lower()

    try:
        # -------------------- MP3 --------------------
        if ext == ".mp3":
            try:
                audio = EasyID3(file_path)
            except ID3NoHeaderError:
                audio = EasyID3()
                audio.save(file_path)
                audio = EasyID3(file_path)

            for key, value in metadata.items():
                if key in EasyID3.valid_keys.keys():
                    audio[key] = value
            audio.save()

            id3 = ID3(file_path)

            if cover_path and dl_cfg.get("embed_cover", True) and os.path.exists(cover_path):
                with open(cover_path, "rb") as img:
                    id3.add(APIC(
                        encoding=3,
                        mime="image/jpeg",
                        type=3,
                        desc="Cover",
                        data=img.read()
                    ))

            if dl_cfg.get("get_lyrics", True) and lyrics:
                if unsynced:
                    id3.add(USLT(
                        encoding=3,
                        lang="eng",
                        desc="Lyrics",
                        text=lyrics
                    ))
                else:
                    save_lrc(file_path, lyrics)

            id3.save()

        # -------------------- FLAC --------------------
        elif ext == ".flac":
            audio = FLAC(file_path)
            for key, value in metadata.items():
                audio[key] = value

            if cover_path and dl_cfg.get("embed_cover", True) and os.path.exists(cover_path):
                pic = Picture()
                pic.type = 3
                pic.mime = "image/jpeg"
                pic.desc = "Cover"
                with open(cover_path, "rb") as img:
                    pic.data = img.read()
                audio.add_picture(pic)

            if dl_cfg.get("get_lyrics", True) and lyrics:
                if unsynced:
                    audio["LYRICS"] = lyrics
                else:
                    save_lrc(file_path, lyrics)

            audio.save()

        else:
            if config.get("debug", False):
                print(f"[tagger] Skipping tag: unsupported format {ext}")
            return False

        return True

    except Exception as e:
        if config.get("debug", False):
            print(f"[tagger] Tagging failed for {file_path}: {e}")
        return False