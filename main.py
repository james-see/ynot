import tkinter as tk
from tkinter import ttk, messagebox
import yt_dlp
import os
import re
import subprocess
import tempfile
from youtube_transcript_api import YouTubeTranscriptApi


class YnotGui:
    def __init__(self, root):
        self.root = root
        self.root.title("YNOT")

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

        # Buttons frame
        self.buttons_frame = ttk.Frame(self.frame)
        self.buttons_frame.grid(row=2, column=0, columnspan=2, pady=10)

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

        # Progress label
        self.progress_label = ttk.Label(self.frame, text="")
        self.progress_label.grid(row=3, column=0, columnspan=2, pady=5)

        # Clickable file path label
        self.file_link = ttk.Label(
            self.frame, text="", foreground="blue", cursor="hand2"
        )
        self.file_link.grid(row=4, column=0, columnspan=2, pady=5)
        self.file_link.bind("<Button-1>", self.open_file_location)
        self.saved_filepath = None

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
            # Create temp file for intermediate TS
            with tempfile.NamedTemporaryFile(suffix=".ts", delete=False) as tmp:
                temp_ts = tmp.name

            # Step 1: Convert to proper TS format
            subprocess.run(
                [
                    "ffmpeg",
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
                    "ffmpeg",
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

    def save_transcript(self, video_id, title):
        """Fetch and save transcript to file."""
        home_dir = os.path.expanduser("~")
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id)
        text = "\n".join([snippet.text for snippet in transcript.snippets])
        filepath = os.path.join(home_dir, f"{title}_transcript.txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
        return filepath

    def download(self):
        url = self.url_entry.get()
        if not url:
            messagebox.showerror("Error", "Please enter a YT URL")
            return

        home_dir = os.path.expanduser("~")

        ydl_opts = {
            "format": "best",
            "outtmpl": os.path.join(home_dir, "%(title)s.%(ext)s"),
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
            self.progress_label.config(text="Downloading...")
            self.file_link.config(text="")
            self.root.update()

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get("title", "video")
                # Get final filename (after remux, extension will be .mp4)
                filename = ydl.prepare_filename(info)
                filename = os.path.splitext(filename)[0] + ".mp4"

            # Convert to proper MP4 format
            self.progress_label.config(text="Converting to proper MP4...")
            self.root.update()
            self.convert_to_proper_mp4(filename)

            # Also download transcript if checkbox is checked
            if self.include_transcript_var.get():
                self.progress_label.config(text="Fetching transcript...")
                self.root.update()
                video_id = self.extract_video_id(url)
                if video_id:
                    try:
                        self.save_transcript(video_id, title)
                    except Exception as e:
                        messagebox.showwarning(
                            "Warning", f"Could not fetch transcript: {e}"
                        )

            # Show saved file path
            self.saved_filepath = filename
            self.progress_label.config(text="Download complete!")
            self.file_link.config(text=f"Saved: {filename}")
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
        url = self.url_entry.get()
        if not url:
            messagebox.showerror("Error", "Please enter a YT URL")
            return

        video_id = self.extract_video_id(url)
        if not video_id:
            messagebox.showerror("Error", "Could not extract video ID from URL")
            return

        try:
            self.progress_label.config(text="Fetching transcript...")
            self.root.update()

            # Get video title using yt-dlp (no download)
            with yt_dlp.YoutubeDL({"skip_download": True, "quiet": True}) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get("title", "video")

            self.save_transcript(video_id, title)
            self.progress_label.config(text="Transcript saved!")
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
