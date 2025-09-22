# dabhounds/core/report.py

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict

CONFIG_DIR = Path.home() / ".dabhound"
REPORT_DIR = CONFIG_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

def md5_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()

def generate_report(input_tracks: List[Dict], matched_tracks: List[Dict], match_results: List[Dict],
                    mode: str, library_name: str, library_id: str, source_url: str):
    """Generate both TXT (verbose) and JSON (minimal) reports with source_url at top-level."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    # TXT report
    lines = [f"DABHounds Conversion Report — {timestamp}",
             f"Source URL: {source_url}",
             f"Matching Mode: {mode.upper()}",
             f"DAB Library ID: {library_id}",
             "-"*60]

    for i, original in enumerate(input_tracks):
        match = match_results[i]
        matched = "FOUND" if match else "NOT FOUND"
        lines.append(f"{i+1}. {original['artist']} - {original['title']}")
        lines.append(f"    ISRC: {original.get('isrc') or 'N/A'}")
        lines.append(f"    Match Status: {matched}")
        if match:
            lines.append(f"    DAB Track: {match['artist']} - {match['title']} (ID: {match['id']})")
        else:
            lines.append("    DAB Track: —")
        lines.append(f"    Source URL: {source_url}")
        lines.append("")

    safe_name = library_name.replace(" ", "_").replace(":", "-")
    txt_path = REPORT_DIR / f"report_{safe_name}.txt"
    with txt_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # JSON report
    json_path = REPORT_DIR / f"report_{md5_hash(source_url)}.json"
    json_data = []
    for i, original in enumerate(input_tracks):
        match = match_results[i]
        json_data.append({
            "artist": original["artist"],
            "title": original["title"],
            "isrc": original.get("isrc"),
            "match_status": "FOUND" if match else "NOT FOUND",
            "dab_track_id": match["id"] if match else None,
            "source_url": source_url
        })
    json_report = {
        "library_name": library_name,
        "library_id": library_id,
        "matching_mode": mode,
        "timestamp": timestamp,
        "source_url": source_url,
        "tracks": json_data
    }
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(json_report, f, indent=2)

    print(f"[DABHound] Saved report to {txt_path} and {json_path}")


def load_report(source_url: str) -> Dict:
    """Load JSON report for a given source_url (by md5)."""
    json_path = REPORT_DIR / f"report_{md5_hash(source_url)}.json"
    if not json_path.exists():
        return {}
    with json_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def append_tracks_to_report(source_url: str, new_tracks: List[Dict], library_id: str, library_name: str, matching_mode: str):
    """Append new tracks to existing JSON report (TXT stays as-is)."""
    report = load_report(source_url)
    if not report:
        # fallback: create new
        return generate_report(
            input_tracks=[t for t in new_tracks],
            matched_tracks=[t for t in new_tracks if t.get("dab_track_id")],
            match_results=[{"id": t.get("dab_track_id")} if t.get("dab_track_id") else None for t in new_tracks],
            mode=matching_mode,
            library_name=library_name,
            library_id=library_id,
            source_url=source_url
        )

    # Append to existing tracks
    for t in new_tracks:
        report["tracks"].append({
            "artist": t["artist"],
            "title": t["title"],
            "isrc": t.get("isrc"),
            "match_status": "FOUND" if t.get("dab_track_id") else "NOT FOUND",
            "dab_track_id": t.get("dab_track_id"),
            "source_url": source_url
        })
    # Update timestamp
    report["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    # Save back
    json_path = REPORT_DIR / f"report_{md5_hash(source_url)}.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"[DABHound] Appended {len(new_tracks)} tracks to JSON report {json_path}")