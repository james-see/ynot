import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import yt_dlp
import os
import re
import subprocess
import tempfile
import shutil
import json
from pathlib import Path
from youtube_transcript_api import YouTubeTranscriptApi

CONFIG_DIR = Path.home() / ".config" / "ynot"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config():
    """Load config from ~/.config/ynot/config.json."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"save_path": str(Path.home())}


def save_config(config):
    """Save config to ~/.config/ynot/config.json."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def sanitize_filename(name):
    """Replace path-unsafe characters so title can be used in file paths."""
    unsafe = '/\\:*?"<>|\x00'
    for c in unsafe:
        name = name.replace(c, "-")
    return name.strip() or "video"


class YnotGui:
    def __init__(self, root):
        self.root = root
        self.root.title("YNOT")
        self.config = load_config()
        self.save_path = Path(
            self.config.get("save_path", str(Path.home()))
        ).expanduser()

        # Check for ffmpeg on startup
        self.check_ffmpeg()

        # Main frame
        self.frame = ttk.Frame(root, padding="10")
        self.frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # URL input
        self.url_label = ttk.Label(self.frame, text="YT URL:")
        self.url_label.grid(row=0, column=0, sticky=tk.W, pady=5)

        self.url_entry = ttk.Entry(self.frame, width=50)
        self.url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)

        # Include Transcript checkbox
        self.include_transcript_var = tk.BooleanVar()
        self.include_transcript_check = ttk.Checkbutton(
            self.frame, text="Include Transcript", variable=self.include_transcript_var
        )
        self.include_transcript_check.grid(row=1, column=0, columnspan=2, pady=5)

        # Batch mode checkbox
        self.batch_mode_var = tk.BooleanVar(value=False)
        self.batch_mode_check = ttk.Checkbutton(
            self.frame,
            text="Batch mode (path to .txt file with URLs, one per line)",
            variable=self.batch_mode_var,
            command=self._on_batch_mode_toggle,
        )
        self.batch_mode_check.grid(row=2, column=0, columnspan=2, pady=5)

        # Buttons frame
        self.buttons_frame = ttk.Frame(self.frame)
        self.buttons_frame.grid(row=3, column=0, columnspan=2, pady=10)

        # Download button
        self.download_button = ttk.Button(
            self.buttons_frame, text="Download", command=self.download
        )
        self.download_button.grid(row=0, column=0, padx=5)

        # Transcript Only button
        self.transcript_button = ttk.Button(
            self.buttons_frame, text="Transcript Only", command=self.download_transcript
        )
        self.transcript_button.grid(row=0, column=1, padx=5)

        # Settings button
        self.settings_button = ttk.Button(
            self.buttons_frame, text="Settings", command=self._open_settings
        )
        self.settings_button.grid(row=0, column=2, padx=5)

        # Progress label
        self.progress_label = ttk.Label(self.frame, text="")
        self.progress_label.grid(row=4, column=0, columnspan=2, pady=5)

        # Clickable file path label
        self.file_link = ttk.Label(
            self.frame, text="", foreground="blue", cursor="hand2"
        )
        self.file_link.grid(row=5, column=0, columnspan=2, pady=5)
        self.file_link.bind("<Button-1>", self.open_file_location)
        self.saved_filepath = None

    def _on_batch_mode_toggle(self):
        if self.batch_mode_var.get():
            self.url_label.config(text="Path to URLs file (.txt):")
        else:
            self.url_label.config(text="YT URL:")

    def _open_settings(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Settings")
        dialog.transient(self.root)
        dialog.grab_set()
        ttk.Label(dialog, text="Save path:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        path_var = tk.StringVar(value=str(self.save_path))
        path_entry = ttk.Entry(dialog, textvariable=path_var, width=50)
        path_entry.grid(row=0, column=1, padx=5, pady=5)

        def browse():
            d = filedialog.askdirectory(initialdir=str(self.save_path))
            if d:
                path_var.set(d)

        ttk.Button(dialog, text="Browse...", command=browse).grid(
            row=0, column=2, padx=5, pady=5
        )

        def save_and_close():
            p = Path(path_var.get()).expanduser()
            if not p.is_dir():
                messagebox.showerror(
                    "Error", f"Path does not exist or is not a directory: {p}"
                )
                return
            self.save_path = p
            self.config["save_path"] = str(p)
            save_config(self.config)
            dialog.destroy()

        ttk.Button(dialog, text="Save", command=save_and_close).grid(
            row=1, column=1, pady=10
        )
        dialog.geometry(
            "+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50)
        )

    def _get_urls_to_process(self):
        """Return list of URLs from entry. Single URL or from batch file."""
        raw = self.url_entry.get().strip()
        if not raw:
            return []
        if self.batch_mode_var.get():
            path = Path(raw).expanduser()
            if not path.exists():
                return None  # signal error
            with open(path, encoding="utf-8") as f:
                return [u.strip() for u in f if u.strip()]
        return [raw]

    def check_ffmpeg(self):
        """Check if ffmpeg is installed and show instructions if not."""
        # Common ffmpeg installation paths
        common_paths = [
            "/opt/homebrew/bin",  # Homebrew on Apple Silicon
            "/usr/local/bin",  # Homebrew on Intel Mac
            "/usr/bin",  # System install
            "/bin",  # Alternative system path
        ]

        # Add common paths to search
        search_path = os.environ.get("PATH", "")
        for path in common_paths:
            if path not in search_path:
                search_path = f"{path}:{search_path}"

        # Try to find ffmpeg
        ffmpeg_path = shutil.which("ffmpeg", path=search_path)

        if not ffmpeg_path:
            message = (
                "ffmpeg is required but not found on your system.\n\n"
                "Installation instructions:\n\n"
                "macOS:\n"
                "  brew install ffmpeg\n\n"
                "Linux:\n"
                "  sudo apt install ffmpeg  (Debian/Ubuntu)\n"
                "  sudo dnf install ffmpeg  (Fedora)\n\n"
                "Windows:\n"
                "  Download from ffmpeg.org and add to PATH\n\n"
                "The app will continue but video conversion may fail."
            )
            messagebox.showwarning("ffmpeg Not Found", message)
        else:
            # Store the ffmpeg path for later use
            self.ffmpeg_path = ffmpeg_path

    def extract_video_id(self, url):
        """Extract video ID from YouTube URL."""
        patterns = [
            r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
            r"(?:embed\/)([0-9A-Za-z_-]{11})",
            r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def open_file_location(self, event=None):
        """Open Finder at the saved file location."""
        if self.saved_filepath and os.path.exists(self.saved_filepath):
            subprocess.run(["open", "-R", self.saved_filepath])

    def convert_to_proper_mp4(self, input_file):
        """Convert MPEG-TS stream to proper MP4 container using two-step process."""
        try:
            # Use stored ffmpeg path or fallback to 'ffmpeg'
            ffmpeg_cmd = getattr(self, "ffmpeg_path", "ffmpeg")

            # Create temp file for intermediate TS
            with tempfile.NamedTemporaryFile(suffix=".ts", delete=False) as tmp:
                temp_ts = tmp.name

            # Step 1: Convert to proper TS format
            subprocess.run(
                [
                    ffmpeg_cmd,
                    "-y",
                    "-i",
                    input_file,
                    "-map",
                    "0:v:0",
                    "-map",
                    "0:a:0",
                    "-c:v",
                    "copy",
                    "-c:a",
                    "copy",
                    "-bsf:v",
                    "h264_mp4toannexb",
                    "-f",
                    "mpegts",
                    temp_ts,
                ],
                check=True,
                capture_output=True,
            )

            # Step 2: Convert TS to proper MP4
            subprocess.run(
                [
                    ffmpeg_cmd,
                    "-y",
                    "-i",
                    temp_ts,
                    "-map",
                    "0:v:0",
                    "-map",
                    "0:a:0",
                    "-c:v",
                    "copy",
                    "-c:a",
                    "copy",
                    "-bsf:v",
                    "h264_metadata=aud=insert",
                    "-movflags",
                    "+faststart",
                    input_file,
                ],
                check=True,
                capture_output=True,
            )

            # Clean up temp file
            os.unlink(temp_ts)
            return True
        except Exception as e:
            print(f"Conversion error: {e}")
            return False

    def save_transcript(self, video_id, title, save_dir=None):
        """Fetch and save transcript to file."""
        save_dir = save_dir or self.save_path
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id)
        text = "\n".join([snippet.text for snippet in transcript.snippets])
        safe_title = sanitize_filename(title)
        filepath = os.path.join(str(save_dir), f"{safe_title}_transcript.txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
        return filepath

    def download(self):
        urls = self._get_urls_to_process()
        if urls is None:
            messagebox.showerror("Error", "Batch file not found. Check the path.")
            return
        if not urls:
            msg = "Path to URLs file (.txt)" if self.batch_mode_var.get() else "YT URL"
            messagebox.showerror("Error", f"Please enter a {msg}")
            return

        out_dir = str(self.save_path)
        ydl_opts = {
            "format": "best",
            "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
            "progress_hooks": [self.progress_hook],
            "postprocessors": [
                {
                    "key": "FFmpegVideoRemuxer",
                    "preferedformat": "mp4",
                }
            ],
            "postprocessor_args": {"VideoRemuxer": ["-movflags", "+faststart"]},
        }

        try:
            self.file_link.config(text="")
            last_file = None
            total = len(urls)
            for i, url in enumerate(urls):
                self.progress_label.config(
                    text=(
                        f"Downloading ({i + 1}/{total})..."
                        if total > 1
                        else "Downloading..."
                    )
                )
                self.root.update()

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    title = info.get("title", "video")
                    filename = ydl.prepare_filename(info)
                    filename = os.path.splitext(filename)[0] + ".mp4"

                self.progress_label.config(
                    text=(
                        f"Converting ({i + 1}/{total})..."
                        if total > 1
                        else "Converting to proper MP4..."
                    )
                )
                self.root.update()
                self.convert_to_proper_mp4(filename)

                if self.include_transcript_var.get():
                    self.progress_label.config(
                        text=(
                            f"Fetching transcript ({i + 1}/{total})..."
                            if total > 1
                            else "Fetching transcript..."
                        )
                    )
                    self.root.update()
                    video_id = self.extract_video_id(url)
                    if video_id:
                        try:
                            self.save_transcript(video_id, title)
                        except Exception as e:
                            messagebox.showwarning(
                                "Warning", f"Could not fetch transcript: {e}"
                            )
                last_file = filename

            self.saved_filepath = last_file
            done_msg = f"Saved {total} file(s)" if total > 1 else "Download complete!"
            self.progress_label.config(text=done_msg)
            self.file_link.config(text=f"Saved: {last_file}" if last_file else "")
            if total == 1:
                self.url_entry.delete(0, tk.END)

        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.progress_label.config(text="")

    def progress_hook(self, d):
        if d["status"] == "downloading":
            percent = d.get("_percent_str", "0%")
            self.progress_label.config(text=f"Downloading... {percent}")
            self.root.update()

    def download_transcript(self):
        urls = self._get_urls_to_process()
        if urls is None:
            messagebox.showerror("Error", "Batch file not found. Check the path.")
            return
        if not urls:
            msg = "Path to URLs file (.txt)" if self.batch_mode_var.get() else "YT URL"
            messagebox.showerror("Error", f"Please enter a {msg}")
            return

        try:
            total = len(urls)
            for i, url in enumerate(urls):
                self.progress_label.config(
                    text=(
                        f"Fetching transcript ({i + 1}/{total})..."
                        if total > 1
                        else "Fetching transcript..."
                    )
                )
                self.root.update()

                video_id = self.extract_video_id(url)
                if not video_id:
                    messagebox.showwarning(
                        "Warning", f"Could not extract video ID: {url}"
                    )
                    continue

                with yt_dlp.YoutubeDL({"skip_download": True, "quiet": True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                    title = info.get("title", "video")

                self.save_transcript(video_id, title)
            done_msg = (
                f"Transcripts saved ({total})" if total > 1 else "Transcript saved!"
            )
            self.progress_label.config(text=done_msg)
            if total == 1:
                self.url_entry.delete(0, tk.END)

        except Exception as e:
            messagebox.showerror("Error", f"Could not fetch transcript: {e}")
            self.progress_label.config(text="")


def main():
    root = tk.Tk()
    app = YnotGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
