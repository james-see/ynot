# YNOT

![ynot](https://github.com/user-attachments/assets/c6b1e264-ae2c-4069-98e2-953fd3798ec1)

A simple YT downloader with a GUI interface.

**[📥 Download for your platform](https://james-see.github.io/ynot/)**

## Features

- Download videos from YouTube
- Download transcripts only (no video)
- Option to include transcript with video download

All files are saved to your home directory (`~/`).

## Installation

### Homebrew (macOS)

```bash
brew tap james-see/tap
brew install --cask ynot
```

### Pre-built Releases

Download the latest release for your platform:

- **Linux**: Download `ynot-x86_64.AppImage`, make it executable (`chmod +x ynot-x86_64.AppImage`), and run it
- **macOS**: Download `ynot-macos.dmg`, open it, and drag YNOT to Applications
- **Windows**: Download `ynot.exe` and run it

### From Source

```bash
pip install -r requirements.txt
python main.py
```

## Building

The project uses GitHub Actions to automatically build releases for Linux (AppImage), macOS (DMG), and Windows (EXE).

To build locally:

```bash
pip install pyinstaller yt-dlp
pyinstaller --onefile --windowed --name ynot main.py
```

## License

![WTFPL](http://www.wtfpl.net/wp-content/uploads/2012/12/wtfpl-badge-4.png)

This project is licensed under the WTFPL license- see the [LICENSE](LICENSE) file for details.

