# Changelog

## [0.7.2] - 2026-11-13

### Added
- Playlist to TXT: dump flat playlist video URLs to a text file (yt-dlp API; works in bundled app).
- Batch interval: seconds between items in batch download/transcript mode to reduce rate-limit errors.

### Fixed
- v0.7.2 release previously shipped GUI controls without the backing methods; playlist and interval logic are now implemented.

## [0.7.1] - 2026-11-13

### Fixed
- Fixed "Requested format is not available" errors on modern YouTube videos by switching the download selector from `best` (single progressive file, often missing now) to a merge selector preferring H.264/AAC streams (`bestvideo[vcodec^=avc1]+bestaudio[ext=m4a]/bestvideo*+bestaudio/best`) with a `best` fallback. Downloads now get higher-quality video+audio, stay MP4/H.264 for player compatibility, and match the H.264-based ffmpeg conversion pipeline.

## [0.6.3] - 2025-12-08

### Fixed
- Fixed ffmpeg detection in bundled app by checking common installation paths (Homebrew, system)
- ffmpeg path is now properly resolved and used for conversions

## [0.6.2] - 2025-12-08

### Fixed
- Properly convert MPEG-TS streams to MP4 using two-step ffmpeg process for Final Cut Pro compatibility

### Added
- ffmpeg availability check with installation instructions

## [0.6.1] - 2025-12-08

### Fixed
- Fixed FFmpegVideoRemuxer parameter typo (prefformat -> preferedformat)

## [0.6.0] - 2025-12-08

### Fixed
- Fixed video downloads saving as MPEG-TS streams with incorrect .mp4 extension
- Videos are now properly remuxed to MP4 container format using yt-dlp's built-in FFmpegVideoRemuxer

### Added
- Added clickable file path after download completes - click to reveal in Finder
- Added `-movflags +faststart` for better web streaming compatibility

## [0.5.1] and earlier

See [GitHub Releases](https://github.com/james-see/ynot/releases) for previous versions.
