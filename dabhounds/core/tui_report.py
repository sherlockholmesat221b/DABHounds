# dabhounds/core/tui_report.py

import sys
import csv
from pathlib import Path
from typing import List, Dict
try:
    import curses
    HAS_CURSES = True
except ImportError:
    HAS_CURSES = False

def export_to_csv(tracks: List[Dict], output_path: Path, misses_only: bool = False):
    """Export tracks to CSV format."""
    filtered_tracks = tracks
    if misses_only:
        filtered_tracks = [t for t in tracks if t.get("match_status") == "NOT FOUND"]
    
    if not filtered_tracks:
        print("[DABHound] No tracks to export.")
        return False
    
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["artist", "title", "isrc", "match_status", "dab_track_id", "track_id"])
        writer.writeheader()
        writer.writerows(filtered_tracks)
    
    return True

def show_terminal_summary(tracks: List[Dict], library_name: str, library_id: str):
    """Show a simple terminal summary focused on missing tracks."""
    misses = [t for t in tracks if t.get("match_status") == "NOT FOUND"]
    found = len(tracks) - len(misses)
    
    print("\n" + "="*60)
    print(f"DABHounds Conversion Summary")
    print("="*60)
    print(f"Library: {library_name}")
    print(f"Library ID: {library_id}")
    print(f"Total Tracks: {len(tracks)}")
    print(f"Found: {found}")
    print(f"Missing: {len(misses)}")
    print("="*60)
    
    if misses:
        print("\nMissing Tracks:")
        print("-"*60)
        for i, track in enumerate(misses, 1):
            print(f"{i}. {track['artist']} - {track['title']}")
            if track.get('isrc'):
                print(f"   ISRC: {track['isrc']}")
        print("-"*60)
    else:
        print("\n✓ All tracks matched successfully!")
    
    print()

def show_tui_report(tracks: List[Dict], library_name: str, library_id: str, source_url: str):
    """Interactive TUI report viewer (curses-based)."""
    if not HAS_CURSES:
        print("[DABHound] TUI not available on this platform. Falling back to terminal summary.")
        show_terminal_summary(tracks, library_name, library_id)
        return
    
    try:
        curses.wrapper(_tui_main, tracks, library_name, library_id, source_url)
    except Exception as e:
        print(f"[DABHound] TUI error: {e}. Falling back to terminal summary.")
        show_terminal_summary(tracks, library_name, library_id)

def _tui_main(stdscr, tracks: List[Dict], library_name: str, library_id: str, source_url: str):
    """Main TUI loop."""
    curses.curs_set(0)
    stdscr.keypad(True)
    stdscr.timeout(100)  # 100ms timeout for getch()
    
    # Initialize colors safely
    try:
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_GREEN, -1)
        curses.init_pair(2, curses.COLOR_RED, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_CYAN, -1)
    except:
        pass
    
    current_filter = "all"  # "all", "found", "missing"
    scroll_pos = 0
    
    def get_filtered_tracks():
        if current_filter == "all":
            return tracks
        elif current_filter == "found":
            return [t for t in tracks if t.get("match_status") == "FOUND"]
        else:  # missing
            return [t for t in tracks if t.get("match_status") == "NOT FOUND"]
    
    while True:
        try:
            stdscr.clear()
            height, width = stdscr.getmaxyx()
            
            # Minimum terminal size check
            if height < 10 or width < 40:
                stdscr.addstr(0, 0, "Terminal too small! Resize to at least 40x10")
                stdscr.refresh()
                key = stdscr.getch()
                if key in [ord('q'), ord('Q'), 27]:  # q or ESC
                    break
                continue
            
            filtered = get_filtered_tracks()
            
            # Header
            title = f"DABHounds Report - {library_name}"
            if len(title) > width - 1:
                title = title[:width-4] + "..."
            stdscr.addstr(0, 0, title, curses.A_BOLD | curses.color_pair(4))
            
            lib_id_text = f"Library ID: {library_id}"
            if len(lib_id_text) > width - 1:
                lib_id_text = lib_id_text[:width-4] + "..."
            stdscr.addstr(1, 0, lib_id_text)
            
            stats_text = f"Total: {len(tracks)} | Found: {len([t for t in tracks if t.get('match_status') == 'FOUND'])} | Missing: {len([t for t in tracks if t.get('match_status') == 'NOT FOUND'])}"
            if len(stats_text) > width - 1:
                stats_text = stats_text[:width-4] + "..."
            stdscr.addstr(2, 0, stats_text)
            
            # Filter indicator
            filter_text = f"Filter: [{current_filter.upper()}]"
            stdscr.addstr(3, 0, filter_text[:width-1], curses.color_pair(3))
            
            # Separator
            sep = "-" * min(width - 1, 80)
            stdscr.addstr(4, 0, sep)
            
            # Track list (scrollable)
            list_start = 5
            list_height = max(1, height - list_start - 4)  # Ensure at least 1 line
            
            # Clamp scroll position
            max_scroll = max(0, len(filtered) - list_height)
            scroll_pos = max(0, min(scroll_pos, max_scroll))
            
            for i in range(min(list_height, len(filtered))):
                track_idx = scroll_pos + i
                if track_idx >= len(filtered):
                    break
                
                track = filtered[track_idx]
                status = track.get("match_status", "NOT FOUND")
                color = curses.color_pair(1) if status == "FOUND" else curses.color_pair(2)
                
                artist = track.get('artist', 'Unknown')
                title = track.get('title', 'Unknown')
                line = f"{track_idx + 1}. {artist} - {title}"
                
                # Truncate if needed
                max_line_len = width - 3
                if len(line) > max_line_len:
                    line = line[:max_line_len-3] + "..."
                
                status_marker = "+" if status == "FOUND" else "-"
                line = f"{status_marker} {line}"
                
                y_pos = list_start + i
                if y_pos < height - 3:
                    try:
                        stdscr.addstr(y_pos, 0, line[:width-1], color)
                    except curses.error:
                        pass
            
            # Footer
            footer_y = height - 3
            if footer_y > list_start:
                sep2 = "-" * min(width - 1, 80)
                stdscr.addstr(footer_y, 0, sep2)
                
                cmd_text = "[A]ll [F]ound [M]issing | [S]ave CSV [E]xport Misses | [Q]uit"
                if len(cmd_text) > width - 1:
                    cmd_text = "[A/F/M] [S/E] [Q]uit"
                stdscr.addstr(footer_y + 1, 0, cmd_text[:width-1], curses.A_BOLD)
            
            stdscr.refresh()
            
            # Get input
            key = stdscr.getch()
            if key == -1:  # timeout
                continue
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            # Debug mode: show error
            try:
                stdscr.addstr(0, 0, f"Error: {str(e)[:width-1]}")
                stdscr.addstr(1, 0, "Press Q to quit")
                stdscr.refresh()
                stdscr.timeout(-1)
                key = stdscr.getch()
                if key in [ord('q'), ord('Q')]:
                    break
            except:
                break
        
        # Handle input
        try:
            if key in [ord('q'), ord('Q'), 27]:  # q, Q, or ESC
                break
            elif key in [ord('a'), ord('A')]:
                current_filter = "all"
                scroll_pos = 0
            elif key in [ord('f'), ord('F')]:
                current_filter = "found"
                scroll_pos = 0
            elif key in [ord('m'), ord('M')]:
                current_filter = "missing"
                scroll_pos = 0
            elif key in [ord('s'), ord('S')]:
                # Save all tracks to CSV
                stdscr.timeout(-1)  # Block for this operation
                output_path = Path.home() / ".dabhound" / "reports" / f"export_{library_name.replace(' ', '_').replace('/', '_')}.csv"
                if export_to_csv(tracks, output_path, misses_only=False):
                    msg = f"Saved to: {output_path}"
                    if len(msg) > width - 1:
                        msg = "Saved! Press any key..."
                    try:
                        stdscr.addstr(footer_y + 2, 0, msg[:width-1], curses.color_pair(1))
                        stdscr.refresh()
                        stdscr.getch()
                    except:
                        pass
                stdscr.timeout(100)
            elif key in [ord('e'), ord('E')]:
                # Export missing tracks only
                stdscr.timeout(-1)
                output_path = Path.home() / ".dabhound" / "reports" / f"misses_{library_name.replace(' ', '_').replace('/', '_')}.csv"
                if export_to_csv(tracks, output_path, misses_only=True):
                    msg = f"Misses saved to: {output_path}"
                    if len(msg) > width - 1:
                        msg = "Misses saved! Press any key..."
                    try:
                        stdscr.addstr(footer_y + 2, 0, msg[:width-1], curses.color_pair(1))
                        stdscr.refresh()
                        stdscr.getch()
                    except:
                        pass
                stdscr.timeout(100)
            elif key == curses.KEY_UP:
                scroll_pos = max(0, scroll_pos - 1)
            elif key == curses.KEY_DOWN:
                scroll_pos = min(max_scroll, scroll_pos + 1)
            elif key == curses.KEY_PPAGE:  # Page Up
                scroll_pos = max(0, scroll_pos - list_height)
            elif key == curses.KEY_NPAGE:  # Page Down
                scroll_pos = min(max_scroll, scroll_pos + list_height)
        except Exception:
            pass