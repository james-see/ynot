# Changelog

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
