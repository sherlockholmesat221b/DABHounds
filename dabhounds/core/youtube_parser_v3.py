# dabhounds/core/youtube_parser_v3.py
from typing import List, Dict, Optional, Tuple
import re
import yt_dlp
import logging
import sys, threading, itertools, time   # <-- add these

# reuse your existing musicbrainz helper if present
try:
    from dabhounds.core.musicbrainz import resolve_track_metadata
except Exception:
    resolve_track_metadata = None

LOG = logging.getLogger("YouTubeParserV3")

# -----------------------
# Spinner utility
# -----------------------
class Spinner:
    def __init__(self, message="Processing..."):
        self.spinner = itertools.cycle(['-', '\\', '|', '/'])
        self.stop_running = False
        self.thread = None
        self.message = message

    def start(self):
        def run():
            while not self.stop_running:
                sys.stdout.write(f"\r{self.message} {next(self.spinner)}")
                sys.stdout.flush()
                time.sleep(0.1)
            sys.stdout.write("\r" + " " * (len(self.message) + 4) + "\r")  # clear
            sys.stdout.flush()
        self.thread = threading.Thread(target=run)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.stop_running = True
        if self.thread:
            self.thread.join()

LOG = logging.getLogger("YouTubeParserV3")


class YouTubeParserV3:
    DEFAULT_CONFIG = {
        "extract_mode": "full",      # "full" or "flat"
        "split_chapters": True,
        "normalize_title": True,
        "use_musicbrainz": True,
        "use_qobuz": False,         # placeholder; not implemented
        "yt_dlp_opts": None,        # override
    }

    TIMESTAMP_RE = re.compile(
        r"(?:(?:^|\n)\s*)(?P<h>\d{1,2}):(?P<m>\d{2}):(?P<s>\d{2})|(?:(?:^|\n)\s*)(?P<m2>\d{1,2}):(?P<s2>\d{2})"
    )
    CHAPTER_LINE_RE = re.compile(
        r"^(?P<time>(?:\d{1,2}:)?\d{1,2}:\d{2})\s+[-–—]\s*(?P<title>.+)$", re.MULTILINE
    )
    SIMPLE_SPLIT_RE = re.compile(r"\s*[-|–—|:]\s*", flags=re.UNICODE)

    def __init__(self, config: Optional[Dict] = None):
        self.config = dict(self.DEFAULT_CONFIG)
        if config:
            self.config.update(config)

        # build yt_dlp options
        default_ydl = {
            "quiet": True,                   # no stdout logging
            "no_warnings": True,             # silence warnings like SABR
            "skip_download": True,
            "extract_flat": self.config["extract_mode"] == "flat",
            "force_generic_extractor": False,
            "nocheckcertificate": True,
            "logger": None,                  # disable custom logger
        }
        if self.config.get("yt_dlp_opts"):
            default_ydl.update(self.config["yt_dlp_opts"])

        self.ydl_opts = default_ydl

    # -----------------------
    # STAGE 1: Raw extraction
    # -----------------------
    def _extract_raw_entries(self, url: str) -> List[Dict]:
        """Return list of raw yt-dlp info dicts for each video entry."""
        spinner = Spinner("[DABHound] Parsing YouTube metadata")
        spinner.start()
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        finally:
            spinner.stop()

        if not info:
            return []

        entries = info.get("entries") or [info]
        cleaned = []
        for e in entries:
            if not e:
                continue
            cleaned.append({
                "title": e.get("title", "").strip(),
                "uploader": e.get("uploader", "").strip(),
                "description": e.get("description", "") or "",
                "duration": e.get("duration"),        # seconds or None
                "id": e.get("id"),
                "isrc": e.get("isrc"),
                "raw": e,
            })
        return cleaned

    # -----------------------
    # STAGE 2: Chapter splitting
    # -----------------------
    def _split_into_chapters(self, raw_entry: Dict) -> List[Dict]:
        """Return list of chapters derived from description timestamps or fallback to single chapter."""
        desc = raw_entry.get("description", "")
        chapters = []

        # Try formal '00:00 - Title' lines first
        for m in self.CHAPTER_LINE_RE.finditer(desc):
            t = m.group("time").strip()
            title = m.group("title").strip()
            seconds = self._timestamp_to_seconds(t)
            if seconds is not None:
                chapters.append({"title": title, "start_sec": seconds})

        if not chapters:
            # Try scanning any timestamps and grab following text to end-of-line
            for m in self.TIMESTAMP_RE.finditer(desc):
                # attempt to capture surrounding text on same line
                span_start = m.start()
                # get the whole line
                line_start = desc.rfind("\n", 0, span_start) + 1
                line_end = desc.find("\n", span_start)
                if line_end == -1:
                    line_end = len(desc)
                line = desc[line_start:line_end].strip()
                # strip the timestamp from line
                # find first non-timestamp substring
                cleaned_line = re.sub(r"^\s*(?:\d{1,2}:)?\d{1,2}:\d{2}\s*[-–—]?\s*", "", line)
                ts_text = m.group(0)
                seconds = self._timestamp_to_seconds(ts_text)
                if seconds is not None and cleaned_line:
                    chapters.append({"title": cleaned_line, "start_sec": seconds})

        # Deduplicate and sort
        if chapters:
            # remove duplicates keyed by start_sec
            seen = {}
            for c in chapters:
                seen[c["start_sec"]] = c["title"]
            chapters = [{"title": t, "start_sec": s} for s, t in sorted(seen.items())]
            return chapters

        # fallback: entire video as one chapter using video title
        return [{"title": raw_entry.get("title", ""), "start_sec": 0}]

    def _timestamp_to_seconds(self, ts: str) -> Optional[int]:
        ts = ts.strip()
        parts = ts.split(":")
        try:
            parts = [int(p) for p in parts]
        except ValueError:
            return None
        if len(parts) == 3:
            h, m, s = parts
        elif len(parts) == 2:
            h = 0
            m, s = parts
        else:
            return None
        return h * 3600 + m * 60 + s

    # ------------------------------------
    # STAGE 3: Title parsing & normalization
    # ------------------------------------
    def _normalize_title(self, raw_title: str) -> Tuple[str, str]:
        """
        Try to split "Artist - Title" or "Title - Artist" (heuristic).
        Returns (artist, title) — empty string if unknown.
        """
        t = raw_title.strip()
        # remove common noise
        t = re.sub(r"\[(official video|official audio|audio|video|lyrics)\]", "", t, flags=re.I)
        t = re.sub(r"\((official video|official audio|audio|video|lyrics|HD|Remastered|Remaster(ed)?)\)", "", t, flags=re.I)
        t = re.sub(r"\bfeat\.?\b", "ft.", t, flags=re.I)
        t = re.sub(r"\s{2,}", " ", t).strip()

        # If pipe or dash present, try to split
        parts = re.split(r"\s[-|–—|:]\s", t, maxsplit=1)
        if len(parts) == 2:
            left, right = parts
            # heuristics: if left looks like an artist (contains commas or 'ft.' or few words) choose it
            if self._looks_like_artist(left, right):
                artist = self._capwords(left)
                title = self._capwords(right)
                return artist, title
            else:
                artist = self._capwords(right)
                title = self._capwords(left)
                return artist, title

        # if no clear split, attempt "Artist — Title" style by searching for "by"
        m = re.search(r"(?P<title>.+)\s+by\s+(?P<artist>.+)$", t, flags=re.I)
        if m:
            return self._capwords(m.group("artist").strip()), self._capwords(m.group("title").strip())

        # otherwise, fallback: no artist parsed
        return "", self._capwords(t)

    def _looks_like_artist(self, left: str, right: str) -> bool:
        # simple heuristic: if left contains commas or 'ft.' or <=4 words and right > 1 word => left likely artist
        if "," in left or "ft." in left.lower() or "feat." in left.lower():
            return True
        left_words = len(left.split())
        right_words = len(right.split())
        if left_words <= 4 and right_words >= 2:
            return True
        return False

    def _capwords(self, s: str) -> str:
        # keep existing capitalization of acronyms (simple approach)
        def cap_word(w):
            if w.isupper() and len(w) <= 4:
                return w
            return w.capitalize()
        return " ".join(cap_word(w) for w in s.split())

    # ------------------------------------
    # STAGE 4: Metadata enrichment (opt)
    # ------------------------------------
    def _enrich_metadata(self, track: Dict) -> Dict:
        # If isrc present — short-circuit
        if track.get("isrc"):
            track.setdefault("note", "")
            track["note"] += "isrc_from_source;"
            track["enrichment_source"] = "source_isrc"
            track["enriched"] = True
            return track

        # MusicBrainz enrichment
        if self.config.get("use_musicbrainz") and resolve_track_metadata:
            artist = track.get("artist") or ""
            title = track.get("title") or ""
            if artist and title:
                try:
                    mb = resolve_track_metadata(title, artist)
                    if mb:
                        # update fields if present
                        if mb.get("title"):
                            track["title"] = mb["title"]
                        if mb.get("artist"):
                            track["artist"] = mb["artist"]
                        if mb.get("isrc"):
                            track["isrc"] = mb["isrc"]
                        if mb.get("duration_ms") and not track.get("duration_sec"):
                            track["duration_sec"] = int(mb["duration_ms"] / 1000)
                        track.setdefault("note", "")
                        track["note"] += "musicbrainz_match;"
                        track["enrichment_source"] = "musicbrainz"
                        track["enriched"] = True
                except Exception as e:
                    LOG.debug("MB enrichment failed: %s", e)

        # Qobuz placeholder (not implemented) — left intentionally blank for future
        # - If use_qobuz: call Qobuz API similarly, set enrichment_source='qobuz'
        return track

    # ------------------------------------
    # STAGE 5: Confidence scoring
    # ------------------------------------
    def _score_track(self, track: Dict) -> float:
        """Return float 0..1 confidence."""
        score = 0.0
        if track.get("isrc"):
            score = max(score, 0.92)
        if track.get("enrichment_source") == "musicbrainz":
            score = max(score, 0.65)
        # if both have artist and title explicitly parsed
        if track.get("artist") and track.get("title"):
            score = max(score, 0.5)
        # if only title exists
        if track.get("title") and not track.get("artist"):
            score = max(score, 0.3)
        # duration presence nudges score up slightly
        if track.get("duration_sec"):
            score += 0.05
        # cap at 0.99
        return min(round(score, 3), 0.99)

    # ------------------------------------
    # STAGE 6: Build final track object
    # ------------------------------------
    def _build_track_object(self, base: Dict, raw_entry: Dict, chapter: Dict) -> Dict:
        youtube_id = raw_entry.get("id")
        duration = base.get("duration_sec") or raw_entry.get("duration")
        track = {
            "title": base.get("title") or "",
            "artist": base.get("artist") or "",
            "isrc": base.get("isrc"),
            "duration_sec": duration,
            "youtube_id": youtube_id,
            "confidence": 0.0,         # placeholder; set later
            "source": "yt",
            "raw_title": raw_entry.get("title"),
            "raw_uploader": raw_entry.get("uploader"),
            "notes": base.get("note", ""),
        }
        # include chapter metadata if relevant
        if chapter and chapter.get("start_sec"):
            track["chapter_start_sec"] = chapter["start_sec"]
        return track

    # ------------------------------------
    # MAIN: parse(url)
    # ------------------------------------
    def parse(self, url: str) -> List[Dict]:
        raw_entries = self._extract_raw_entries(url)
        all_tracks: List[Dict] = []

        for raw in raw_entries:
            chapters = [{"title": raw["title"], "start_sec": 0}]
            if self.config.get("split_chapters"):
                chapters = self._split_into_chapters(raw)

            for chap in chapters:
                # choose initial artist/title
                if self.config.get("normalize_title"):
                    parsed_artist, parsed_title = self._normalize_title(chap["title"])
                    # if normalization failed to find artist, fallback to uploader
                    if not parsed_artist:
                        parsed_artist = raw.get("uploader", "") or ""
                else:
                    parsed_artist = raw.get("uploader", "") or ""
                    parsed_title = chap["title"]

                base = {
                    "title": parsed_title,
                    "artist": parsed_artist,
                    "duration_sec": raw.get("duration"),
                    "isrc": raw.get("isrc"),
                    "note": "",
                }

                # enrichment
                base = self._enrich_metadata(base)

                # build final object and score it
                track_obj = self._build_track_object(base, raw, chap)
                track_obj["confidence"] = self._score_track(track_obj)

                # keep provenance for debugging
                track_obj["_provenance"] = {
                    "raw_id": raw.get("id"),
                    "chapter_title": chap.get("title"),
                    "enrichment_source": base.get("enrichment_source"),
                }

                all_tracks.append(track_obj)

        return all_tracks


# small self-test when run directly
if __name__ == "__main__":
    import json, sys
    logging.basicConfig(level=logging.DEBUG)
    if len(sys.argv) < 2:
        print("usage: python youtube_parser_v3.py <youtube-url>")
        sys.exit(1)
    p = YouTubeParserV3()
    res = p.parse(sys.argv[1])
    print(json.dumps(res, indent=2))