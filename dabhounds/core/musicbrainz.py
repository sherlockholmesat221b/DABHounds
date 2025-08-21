# dabhounds/core/musicbrainz.py

import musicbrainzngs

musicbrainzngs.set_useragent("DABHounds", "1.0", "https://github.com/your/project")

def resolve_track_metadata(title: str, artist: str) -> dict | None:
    """Attempt to resolve canonical metadata using MusicBrainz."""
    try:
        result = musicbrainzngs.search_recordings(
            recording=title,
            artist=artist,
            limit=1
        )
        recordings = result.get("recording-list", [])
        if not recordings:
            return None

        rec = recordings[0]
        return {
            "title": rec.get("title"),
            "artist": rec.get("artist-credit", [{}])[0].get("name"),
            "isrc": rec.get("isrc-list", [None])[0],
            "duration_ms": int(rec["length"]) if "length" in rec else None
        }
    except Exception as e:
        print(f"[MusicBrainz] Error resolving '{artist} - {title}': {e}")
        return None