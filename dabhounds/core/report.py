# dabhounds/core/report.py

from typing import List, Dict, Set
from datetime import datetime
from pathlib import Path

# Define user config/report directory
CONFIG_DIR = Path.home() / ".dabhound"
REPORT_DIR = CONFIG_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)  # Create if missing

def _safe_library_filename(library_name: str) -> str:
    safe_library_name = library_name.replace(" ", "_").replace(":", "-")
    return f"report_{safe_library_name}.txt"

def generate_report(input_tracks: List[Dict],
                    matched_tracks: List[Dict],
                    match_results: List[Dict],
                    mode: str,
                    library_name: str,
                    library_id: str,
                    source_url: str):
    """
    Create a fresh report (overwrites if same filename exists).
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"DABHounds Conversion Report — {timestamp}",
             f"Source: {source_url}",
             f"Matching Mode: {mode.upper()}",
             f"DAB Library ID: {library_id}",
             "-" * 60]

    for i, original in enumerate(input_tracks):
        match = match_results[i] if i < len(match_results) else None
        matched = "FOUND" if match else "NOT FOUND"

        lines.append(f"{i + 1}. {original.get('artist','')} - {original.get('title','')}")
        lines.append(f"    ISRC: {original.get('isrc') or 'N/A'}")
        lines.append(f"    Source URL: {original.get('source_id') or 'N/A'}")
        lines.append(f"    Match Status: {matched}")

        if match:
            lines.append(f"    DAB Track: {match.get('artist','')} - {match.get('title','')} (ID: {match.get('id')})")
        else:
            lines.append("    DAB Track: —")

        lines.append("")

    report_path = REPORT_DIR / _safe_library_filename(library_name)

    with report_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[DABHound] Saved match report to {report_path}")
    return report_path

# ---- New helper: scan all reports for a matching Source line ----
def find_reports_for_source(source_url: str) -> List[Path]:
    """
    Search every .txt file in REPORT_DIR for a line starting with 'Source:'
    that exactly matches source_url. Returns a list of matching Path objects,
    sorted by modification time (newest first).
    """
    matches: List[Path] = []
    for p in REPORT_DIR.glob("*.txt"):
        try:
            with p.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("Source:"):
                        # Extract remainder after "Source:"
                        existing = line.split("Source:", 1)[1].strip()
                        if existing == source_url:
                            matches.append(p)
                        break  # stop reading further lines in this file
        except Exception:
            # ignore read errors and continue scanning other files
            continue

    # sort newest-first
    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matches

def load_source_ids_from_report(report_path: Path) -> Set[str]:
    """
    Parse a report and return the set of all Source URL values already recorded in it.
    (This looks for lines that start with 'Source URL:' in the body of the report.)
    """
    existing_ids = set()
    try:
        with report_path.open("r", encoding="utf-8") as f:
            for line in f:
                l = line.strip()
                if l.startswith("Source URL:"):
                    # get everything after "Source URL:"
                    sid = l.split("Source URL:", 1)[1].strip()
                    if sid:
                        existing_ids.add(sid)
    except Exception:
        pass
    return existing_ids

def append_to_report(report_path: Path,
                     new_tracks: List[Dict],
                     new_match_results: List[Dict],
                     library_id: str,
                     mode: str):
    """
    Append a sync block for new_tracks to an existing report file.
    new_tracks and new_match_results must be aligned (same length).
    """
    if not new_tracks:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = []
    lines.append("")
    lines.append(f"[DABHounds Sync — {timestamp}]")
    lines.append(f"Matching Mode: {mode.upper()}")
    lines.append(f"DAB Library ID: {library_id}")
    lines.append("-" * 60)

    for i, track in enumerate(new_tracks):
        match = new_match_results[i] if i < len(new_match_results) else None
        matched = "FOUND" if match else "NOT FOUND"

        lines.append(f"{track.get('artist','')} - {track.get('title','')}")
        lines.append(f"    ISRC: {track.get('isrc') or 'N/A'}")
        lines.append(f"    Source URL: {track.get('source_id') or 'N/A'}")
        lines.append(f"    Match Status: {matched}")
        if match:
            lines.append(f"    DAB Track: {match.get('artist','')} - {match.get('title','')} (ID: {match.get('id')})")
        else:
            lines.append("    DAB Track: —")
        lines.append("")

    try:
        with report_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"[DABHound] Appended {len(new_tracks)} tracks to {report_path}")
    except Exception as e:
        print(f"[DABHound] Failed to append to report: {e}")