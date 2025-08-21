# dabhounds/core/report.py

from typing import List, Dict
from datetime import datetime
from pathlib import Path

# Define user config/report directory
CONFIG_DIR = Path.home() / ".dabhound"
REPORT_DIR = CONFIG_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)  # Create if missing

def generate_report(input_tracks: List[Dict], matched_tracks: List[Dict], match_results: List[Dict], mode: str, library_name: str, library_id: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"DABHounds Conversion Report — {timestamp}",
             f"Matching Mode: {mode.upper()}",
             f"DAB Library ID: {library_id}",
             "-" * 60]

    for i, original in enumerate(input_tracks):
        match = match_results[i]
        matched = "FOUND" if match else "NOT FOUND"

        lines.append(f"{i + 1}. {original['artist']} - {original['title']}")
        lines.append(f"    ISRC: {original.get('isrc') or 'N/A'}")
        lines.append(f"    Match Status: {matched}")

        if match:
            lines.append(f"    DAB Track: {match['artist']} - {match['title']} (ID: {match['id']})")
        else:
            lines.append("    DAB Track: —")

        lines.append("")

    # Make filename safe
    safe_library_name = library_name.replace(" ", "_").replace(":", "-")
    report_path = REPORT_DIR / f"report_{safe_library_name}.txt"

    with report_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[DABHound] Saved match report to {report_path}")