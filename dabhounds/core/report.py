# dabhounds/core/report.py

import json
import hashlib
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict

from dabhounds.core.tui_report import show_tui_report, show_terminal_summary
from dabhounds.core.auth import load_config

CONFIG_DIR = Path.home() / ".dabhound"
REPORT_DIR = CONFIG_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

def md5_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()

def generate_report(input_tracks: List[Dict], matched_tracks: List[Dict], match_results: List[Dict],
                    mode: str, library_name: str, library_id: str, source_url: str):
    """Generate both TXT (verbose) and JSON (minimal) reports using per-track unique IDs."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Build track data for reports
    json_data = []
    for i, original in enumerate(input_tracks):
        match = match_results[i]
        track_id = original.get("track_id") or f"{original['artist']} - {original['title']}"
        json_data.append({
            "artist": original["artist"],
            "title": original["title"],
            "isrc": original.get("isrc"),
            "track_id": track_id,
            "match_status": "FOUND" if match else "NOT FOUND",
            "dab_track_id": match["id"] if match else None
        })
    
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
        # Include per-track ID for clarity
        lines.append(f"    Track ID: {original.get('track_id', 'N/A')}")
        lines.append("")

    safe_name = library_name.replace(" ", "_").replace(":", "-")
    txt_path = REPORT_DIR / f"report_{safe_name}.txt"
    with txt_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # JSON report
    json_path = REPORT_DIR / f"report_{md5_hash(source_url)}.json"
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
    
    # Show TUI or terminal summary based on config
    cfg = load_config()
    if cfg.get("SHOW_TUI_OUTPUT", True):
        if cfg.get("TUI_FALLBACK_TO_TERMINAL", True):
            # Try TUI, fall back to terminal summary if it fails
            show_tui_report(json_data, library_name, library_id, source_url)
        else:
            # Only show TUI if available
            try:
                import curses
                show_tui_report(json_data, library_name, library_id, source_url)
            except ImportError:
                print("[DABHound] TUI not available. Set TUI_FALLBACK_TO_TERMINAL=true in config to show terminal summary.")
    else:
        # Just show terminal summary of missing tracks
        show_terminal_summary(json_data, library_name, library_id)


def load_report(source_url: str) -> Dict:
    """Load JSON report for a given source_url (by md5)."""
    json_path = REPORT_DIR / f"report_{md5_hash(source_url)}.json"
    if not json_path.exists():
        return {}
    with json_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def append_tracks_to_report(source_url: str, new_tracks: List[Dict], library_id: str, library_name: str, matching_mode: str):
    """Append new tracks to existing JSON report and update TXT report."""
    report = load_report(source_url)

    # fallback: create new report if none exists
    if not report:
        return generate_report(
            input_tracks=[t for t in new_tracks],
            matched_tracks=[t for t in new_tracks if t.get("dab_track_id")],
            match_results=[{"id": t.get("dab_track_id")} if t.get("dab_track_id") else None for t in new_tracks],
            mode=matching_mode,
            library_name=library_name,
            library_id=library_id,
            source_url=source_url
        )

    # deduplicate by track_id
    existing_ids = {t.get("track_id") for t in report.get("tracks", [])}
    appended_count = 0

    for t in new_tracks:
        track_id = t.get("track_id") or f"{t['artist']} - {t['title']}"
        if track_id not in existing_ids:
            report["tracks"].append({
                "artist": t["artist"],
                "title": t["title"],
                "isrc": t.get("isrc"),
                "track_id": track_id,
                "match_status": "FOUND" if t.get("dab_track_id") else "NOT FOUND",
                "dab_track_id": t.get("dab_track_id")
            })
            existing_ids.add(track_id)
            appended_count += 1

    # update timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    report["timestamp"] = timestamp

    # save JSON report
    json_path = REPORT_DIR / f"report_{md5_hash(source_url)}.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # save TXT report
    lines = [
        f"DABHounds Conversion Report — {timestamp}",
        f"Source URL: {source_url}",
        f"Matching Mode: {matching_mode.upper()}",
        f"DAB Library ID: {library_id}",
        "-"*60
    ]
    for i, t in enumerate(report["tracks"], start=1):
        lines.append(f"{i}. {t['artist']} - {t['title']}")
        lines.append(f"    ISRC: {t.get('isrc') or 'N/A'}")
        lines.append(f"    Match Status: {t.get('match_status', 'NOT FOUND')}")
        if t.get("dab_track_id"):
            lines.append(f"    DAB Track: {t['artist']} - {t['title']} (ID: {t['dab_track_id']})")
        else:
            lines.append("    DAB Track: —")
        lines.append(f"    Track ID: {t.get('track_id', 'N/A')}")
        lines.append("")

    safe_name = library_name.replace(" ", "_").replace(":", "-")
    txt_path = REPORT_DIR / f"report_{safe_name}.txt"
    with txt_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[DABHound] Appended {appended_count} new tracks to JSON report {json_path} and TXT report {txt_path}")
    
    # Show TUI or terminal summary
    cfg = load_config()
    if cfg.get("SHOW_TUI_OUTPUT", True):
        if cfg.get("TUI_FALLBACK_TO_TERMINAL", True):
            show_tui_report(report["tracks"], library_name, library_id, source_url)
        else:
            try:
                import curses
                show_tui_report(report["tracks"], library_name, library_id, source_url)
            except ImportError:
                print("[DABHound] TUI not available. Set TUI_FALLBACK_TO_TERMINAL=true in config to show terminal summary.")
    else:
        show_terminal_summary(report["tracks"], library_name, library_id)

def delete_report(link: str):
    """Delete old report files (txt and json) associated with a link."""
    hash_val = md5_hash(link)
    
    deleted_any = False
    for ext in [".json", ".txt"]:
        for file in REPORT_DIR.glob(f"*{hash_val}*{ext}"):
            try:
                os.remove(file)
                deleted_any = True
            except Exception:
                pass

    if deleted_any:
        print(f"[DABHound] Old report(s) for this link removed.")