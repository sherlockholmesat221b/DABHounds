# Changelog

All notable changes to this project will be documented in this file.

## [2.0.2] - 2025-08-21
### Added
- Introduced `core/YouTubeParserV3.py` to replace `core/youtube.py`.  
  - Handles YouTube chapters.  
  - Sanitizes titles more accurately.  
  - More robust parsing of playlists and individual videos.

### Changed
- Suppressed yt-dlp SABR warnings during YouTube playlist conversions.

### Released
- Published version 2.0.2 to PyPI.
