# dabhounds/core/report.py

from pathlib import Path
from datetime import datetime
import json
import hashlib

REPORT_DIR = Path.home() / ".dabhound" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

def generate_report(input_tracks, matched_tracks, match_results, mode, library_name, library_id, source_url):
    """
    Generates both a human-readable .txt and a machine-readable .json report.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"DABHounds Conversion Report — {timestamp}",
        f"Source URL: {source_url}",
        f"Matching Mode: {mode.upper()}",
        f"DAB Library ID: {library_id}",
        "-" * 60
    ]

    for i, original in enumerate(input_tracks):
        match = match_results[i]
        matched = "FOUND" if match else "NOT FOUND"
        lines.append(f"{i+1}. {original.get('artist','')} - {original.get('title','')}")
        lines.append(f"    ISRC: {original.get('isrc','N/A')}")
        lines.append(f"    Match Status: {matched}")
        if match:
            lines.append(f"    DAB Track: {match.get('artist','')} - {match.get('title','')} (ID: {match.get('id','')})")
        else:
            lines.append("    DAB Track: —")
        lines.append("")

    # Make a hash of the source URL for unique filename
    url_hash = hashlib.md5(source_url.encode("utf-8")).hexdigest()
    safe_library_name = library_name.replace(" ", "_").replace(":", "-")

    txt_path = REPORT_DIR / f"report_{safe_library_name}_{url_hash}.txt"
    json_path = REPORT_DIR / f"report_{safe_library_name}_{url_hash}.json"

    with txt_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    with json_path.open("w", encoding="utf-8") as f:
        json.dump({
            "source_url": source_url,
            "library_name": library_name,
            "library_id": library_id,
            "timestamp": timestamp,
            "tracks": [
                {
                    "input": t,
                    "matched": m
                } for t, m in zip(input_tracks, match_results)
            ]
        }, f, indent=2)

    print(f"[DABHound] Saved report: {txt_path} and {json_path}")