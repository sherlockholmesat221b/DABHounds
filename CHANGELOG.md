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

## [2.0.3] - 2025-08-23
### Changed
-  Added a proper user agent string. 

## [2.0.4] - 2025-08-24
### Fixed
-  Fixed Spotify OAuth. Hardcoded client credentials.
-  Fixed update atguement in cli.py to be pip compatible.

## [2.0.5] - 2025-09-06
### Changed
 - Updated [squid.wtf](https://qobuz.squid.wtf) API base to the latest API.

### Fixed
 - Fixed the squid.wtf url typo in `README.md`.
