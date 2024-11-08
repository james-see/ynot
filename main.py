import tkinter as tk
from tkinter import ttk, messagebox
import yt_dlp
import os

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
        
        # Download button
        self.download_button = ttk.Button(self.frame, text="Download", command=self.download)
        self.download_button.grid(row=1, column=0, columnspan=2, pady=10)
        
        # Progress label
        self.progress_label = ttk.Label(self.frame, text="")
        self.progress_label.grid(row=2, column=0, columnspan=2, pady=5)

    def download(self):
        url = self.url_entry.get()
        if not url:
            messagebox.showerror("Error", "Please enter a YT URL")
            return
            
        home_dir = os.path.expanduser("~")
        
        ydl_opts = {
            'format': 'best',
            'outtmpl': os.path.join(home_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
        }
        
        try:
            self.progress_label.config(text="Downloading...")
            self.root.update()
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
            self.progress_label.config(text="Download complete!")
            self.url_entry.delete(0, tk.END)
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.progress_label.config(text="")

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0%')
            self.progress_label.config(text=f"Downloading... {percent}")
            self.root.update()

def main():
    root = tk.Tk()
    app = YnotGui(root)
    root.mainloop()

if __name__ == "__main__":
    main()
