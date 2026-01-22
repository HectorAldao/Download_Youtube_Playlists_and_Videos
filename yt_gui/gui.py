import re
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from .config import DownloadOptions
from .runner import YtDlpRunner
from .utils import expand_path


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("YouTube Downloader (yt-dlp)")
        self.geometry("900x650")

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.runner = YtDlpRunner(self.log_queue)

        self.worker_thread: threading.Thread | None = None

        self._build_ui()
        self._poll_log_queue()

    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 6}

        # Top frame: options
        frm = ttk.Frame(self)
        frm.pack(fill="x", **pad)

        # URL
        ttk.Label(frm, text="URL (playlist or video):").grid(row=0, column=0, sticky="w")
        self.url_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.url_var, width=80).grid(row=0, column=1, columnspan=3, sticky="we")

        # Mode
        ttk.Label(frm, text="Mode:").grid(row=1, column=0, sticky="w")
        self.mode_var = tk.StringVar(value="auto")
        mode_frame = ttk.Frame(frm)
        mode_frame.grid(row=1, column=1, columnspan=3, sticky="w")
        ttk.Radiobutton(mode_frame, text="Auto-detect", variable=self.mode_var, value="auto").pack(side="left", padx=(0, 10))
        ttk.Radiobutton(mode_frame, text="Force playlist", variable=self.mode_var, value="playlist").pack(side="left", padx=(0, 10))
        ttk.Radiobutton(mode_frame, text="Force single video", variable=self.mode_var, value="video").pack(side="left")

        # Parallelism
        ttk.Label(mode_frame, text="Workers:").pack(side="left", padx=(20, 5))
        self.workers_var = tk.IntVar(value=1)
        ttk.Spinbox(mode_frame, from_=1, to=32, textvariable=self.workers_var, width=5).pack(side="left")

        # Output directory
        ttk.Label(frm, text="Output folder:").grid(row=2, column=0, sticky="w")
        self.out_var = tk.StringVar(value=expand_path("~/Downloads"))
        out_entry = ttk.Entry(frm, textvariable=self.out_var, width=60)
        out_entry.grid(row=2, column=1, sticky="we")
        ttk.Button(frm, text="Browse…", command=self._browse_output).grid(row=2, column=2, sticky="w")

        # Download archive
        ttk.Label(frm, text="Download archive (optional):").grid(row=3, column=0, sticky="w")
        self.archive_var = tk.StringVar(value="")
        ttk.Entry(frm, textvariable=self.archive_var, width=60).grid(row=3, column=1, sticky="we")
        ttk.Button(frm, text="Pick file…", command=self._browse_archive).grid(row=3, column=2, sticky="w")

        # Cookies-from-browser
        ttk.Label(frm, text="Cookies from browser (optional):").grid(row=4, column=0, sticky="w")
        self.cookies_var = tk.StringVar(value="")
        self.cookies_combo = ttk.Combobox(
            frm,
            textvariable=self.cookies_var,
            values=["", "chrome", "firefox", "edge", "brave", "chromium"],
            width=18,
            state="readonly",
        )
        self.cookies_combo.grid(row=4, column=1, sticky="w")
        ttk.Label(frm, text="(helps with consent/age gates on some setups)").grid(row=4, column=2, columnspan=2, sticky="w")

        # Audio-only + format
        self.audio_only_var = tk.BooleanVar(value=True)
        self.audio_format_var = tk.StringVar(value="mp3")
        audio_frame = ttk.Frame(frm)
        audio_frame.grid(row=5, column=0, columnspan=4, sticky="w")
        ttk.Checkbutton(audio_frame, text="Audio only", variable=self.audio_only_var, command=self._sync_audio_state).pack(side="left")
        ttk.Label(audio_frame, text="Format:").pack(side="left", padx=(12, 6))
        self.audio_format_combo = ttk.Combobox(
            audio_frame,
            textvariable=self.audio_format_var,
            values=["mp3", "m4a", "opus", "wav", "flac"],
            width=8,
            state="readonly",
        )
        self.audio_format_combo.pack(side="left")

        # Subtitles
        self.subs_var = tk.BooleanVar(value=False)
        self.subs_lang_var = tk.StringVar(value="en.*")
        subs_frame = ttk.Frame(frm)
        subs_frame.grid(row=6, column=0, columnspan=4, sticky="w")
        ttk.Checkbutton(subs_frame, text="Download subtitles (if available)", variable=self.subs_var, command=self._sync_subs_state).pack(side="left")
        ttk.Label(subs_frame, text="Languages:").pack(side="left", padx=(12, 6))
        self.subs_lang_entry = ttk.Entry(subs_frame, textvariable=self.subs_lang_var, width=20)
        self.subs_lang_entry.pack(side="left")

        # Embed metadata
        self.embed_meta_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm, text="Embed metadata + thumbnail (when possible)", variable=self.embed_meta_var).grid(
            row=7, column=0, columnspan=4, sticky="w"
        )

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", **pad)
        self.start_btn = ttk.Button(btn_frame, text="Start download", command=self._start)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self._stop, state="disabled")
        self.stop_btn.pack(side="left", padx=(10, 0))
        self.clear_btn = ttk.Button(btn_frame, text="Clear log", command=self._clear_log)
        self.clear_btn.pack(side="left", padx=(10, 0))
        
        # Progress Label
        self.progress_var = tk.StringVar(value="")
        ttk.Label(btn_frame, textvariable=self.progress_var, font=("TkDefaultFont", 9, "bold")).pack(side="left", padx=(20, 0))

        # Log area
        log_frame = ttk.Frame(self)
        log_frame.pack(fill="both", expand=True, **pad)

        ttk.Label(log_frame, text="Log:").pack(anchor="w")
        self.log_text = tk.Text(log_frame, wrap="word")
        self.log_text.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scroll.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scroll.set)

        # Layout tweaks
        frm.columnconfigure(1, weight=1)
        self._sync_audio_state()
        self._sync_subs_state()

    def _browse_output(self) -> None:
        folder = filedialog.askdirectory(initialdir=expand_path(self.out_var.get() or "~/Downloads"))
        if folder:
            self.out_var.set(folder)

    def _browse_archive(self) -> None:
        file_path = filedialog.asksaveasfilename(
            initialdir=expand_path(self.out_var.get() or "~/Downloads"),
            title="Choose download archive file",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if file_path:
            self.archive_var.set(file_path)

    def _sync_audio_state(self) -> None:
        state = "readonly" if self.audio_only_var.get() else "disabled"
        self.audio_format_combo.configure(state=state)

    def _sync_subs_state(self) -> None:
        self.subs_lang_entry.configure(state=("normal" if self.subs_var.get() else "disabled"))

    def _append_log(self, msg: str) -> None:
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")

    def _clear_log(self) -> None:
        self.log_text.delete("1.0", "end")

    def _set_running(self, running: bool) -> None:
        self.start_btn.configure(state=("disabled" if running else "normal"))
        self.stop_btn.configure(state=("normal" if running else "disabled"))

    def _validate(self) -> DownloadOptions | None:
        url = (self.url_var.get() or "").strip()
        if not url:
            messagebox.showerror("Missing URL", "Please paste a YouTube playlist or video URL.")
            return None

        out_dir = expand_path(self.out_var.get() or "")
        if not out_dir:
            messagebox.showerror("Missing output folder", "Please choose an output folder.")
            return None

        opt = DownloadOptions(
            url=url,
            output_dir=out_dir,
            mode=self.mode_var.get(),
            audio_only=bool(self.audio_only_var.get()),
            audio_format=self.audio_format_var.get(),
            subtitles=bool(self.subs_var.get()),
            subs_langs=self.subs_lang_var.get(),
            embed_metadata=bool(self.embed_meta_var.get()),
            download_archive=self.archive_var.get(),
            cookies_from_browser=self.cookies_var.get(),
            workers=self.workers_var.get(),
        )
        return opt

    def _start(self) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            return

        opt = self._validate()
        if not opt:
            return

        self._set_running(True)
        self._append_log("Starting...\n")

        def worker() -> None:
            try:
                rc = self.runner.run(opt)
                self.log_queue.put(f"\nDone. Exit code: {rc}")
            except Exception as e:
                self.log_queue.put(f"\nERROR: {e}")
            finally:
                self.log_queue.put("__GUI_DONE__")

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()

    def _stop(self) -> None:
        self._append_log("Stop requested...")
        self.runner.stop()

    def _poll_log_queue(self) -> None:
        try:
            while True:
                msg = self.log_queue.get_nowait()
                if msg == "__GUI_DONE__":
                    self._set_running(False)
                else:
                    self._append_log(msg)
                    # Attempt to parse progress "Downloading video X of Y"
                    # Pattern matches: "[download] Downloading video 1 of 5" or "... item 1 of 5"
                    match = re.search(r'Downloading (?:video|item) (\d+) of (\d+)', msg)
                    if match:
                        current = match.group(1)
                        total = match.group(2)
                        self.progress_var.set(f"Progress: {current} / {total} songs downloaded")
        except queue.Empty:
            pass
        self.after(120, self._poll_log_queue)


def main_gui() -> int:
    # On Windows, make sure the GUI doesn't open a console if you run pythonw.exe
    app = App()
    app.mainloop()
    return 0
