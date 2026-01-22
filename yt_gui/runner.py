import json
import os
import queue
import subprocess
import time
import threading
import concurrent.futures
from typing import List
from .config import DownloadOptions
from .utils import which_or_none, safe_mkdir, expand_path

class YtDlpRunner:
    def __init__(self, log_queue: queue.Queue[str]) -> None:
        self.log_queue = log_queue
        self.proc: subprocess.Popen[str] | None = None
        self._active_procs: List[subprocess.Popen[str]] = []
        self._proc_lock = threading.Lock()
        self._stop_requested = False

    def _register_proc(self, proc: subprocess.Popen[str]) -> None:
        with self._proc_lock:
            self._active_procs.append(proc)

    def _unregister_proc(self, proc: subprocess.Popen[str]) -> None:
        with self._proc_lock:
            if proc in self._active_procs:
                self._active_procs.remove(proc)

    def stop(self) -> None:
        self._stop_requested = True
        self._log("Stopping all downloads...")
        with self._proc_lock:
            for p in self._active_procs:
                if p.poll() is None:
                    try:
                        p.terminate()
                    except Exception:
                        pass
        
        # Legacy/Fallback
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass

    def _log(self, msg: str) -> None:
        self.log_queue.put(msg)

    def check_deps(self) -> None:
        if not which_or_none("yt-dlp"):
            raise RuntimeError("yt-dlp not found in PATH. Install with: python -m pip install -U yt-dlp")
        if not which_or_none("ffmpeg"):
            raise RuntimeError("ffmpeg not found in PATH. Install ffmpeg and ensure it is in PATH.")

    def probe_url_type(self, url: str, cookies_from_browser: str = "") -> str:
        """
        Returns "playlist" or "video" using yt-dlp JSON output.
        Uses --flat-playlist to keep it lightweight when possible.
        """
        cmd = ["yt-dlp", "-J", "--no-warnings", "--flat-playlist", "--skip-download", url]
        if cookies_from_browser:
            cmd += ["--cookies-from-browser", cookies_from_browser]

        self._log("Probing URL type...")
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
            info = json.loads(out)
            t = info.get("_type", "")
            # yt-dlp uses _type like "playlist" for playlists; for single videos it often has no _type or "video"
            if t == "playlist":
                return "playlist"
            return "video"
        except subprocess.CalledProcessError as e:
            self._log("Probe failed; falling back to auto behavior.\n" + (e.output or ""))
            return "video"
        except Exception as e:
            self._log(f"Probe failed; falling back to auto behavior. ({e})")
            return "video"

    def _get_common_flags(self, opt: DownloadOptions) -> List[str]:
        cmd = ["yt-dlp", "--ignore-errors", "--no-part", "--newline"]
        if opt.cookies_from_browser:
            cmd += ["--cookies-from-browser", opt.cookies_from_browser]
        if opt.download_archive.strip():
            cmd += ["--download-archive", expand_path(opt.download_archive)]
        if opt.embed_metadata:
            cmd += ["--embed-metadata", "--embed-thumbnail"]
        if opt.subtitles:
            cmd += ["--write-subs", "--write-auto-subs", "--sub-langs", opt.subs_langs.strip() or "en.*", "--embed-subs"]
        if opt.audio_only:
            cmd += ["-x", "--audio-format", opt.audio_format.strip() or "mp3"]
        return cmd

    def _run_cmd(self, cmd: List[str]) -> int:
        if self._stop_requested:
            return 1
        
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, universal_newlines=True
        )
        self._register_proc(process)

        assert process.stdout is not None
        for line in process.stdout:
            if self._stop_requested:
                process.terminate()
                break
            self._log(line.rstrip("\n"))

        rc = process.wait()
        self._unregister_proc(process)
        return rc

    def build_cmd(self, opt: DownloadOptions, resolved_type: str) -> List[str]:
        # Legacy/Single builder
        safe_mkdir(opt.output_dir)
        if resolved_type == "playlist":
            outtmpl = os.path.join(opt.output_dir, "%(playlist_title)s", "%(playlist_index)03d - %(title)s.%(ext)s")
        else:
            outtmpl = os.path.join(opt.output_dir, "%(title)s.%(ext)s")

        cmd = self._get_common_flags(opt)
        cmd += ["-o", outtmpl, opt.url]

        if opt.mode == "playlist":
            cmd.insert(1, "--yes-playlist")
        elif opt.mode == "video":
            cmd.insert(1, "--no-playlist")
        return cmd

    def run_parallel(self, opt: DownloadOptions) -> int:
        self._log(f"Preparing parallel download (workers={opt.workers})...")
        
        probe_cmd = ["yt-dlp", "-J", "--flat-playlist", "--no-warnings", opt.url]
        if opt.cookies_from_browser:
            probe_cmd += ["--cookies-from-browser", opt.cookies_from_browser]
            
        try:
            out = subprocess.check_output(probe_cmd, stderr=subprocess.STDOUT, text=True)
            info = json.loads(out)
        except Exception as e:
            self._log(f"Failed to fetch playlist info: {e}")
            return 1
            
        entries = info.get("entries")
        if not entries:
            self._log("No entries found.")
            return 0
            
        playlist_title = info.get("title", "Unknown_Playlist")
        safe_title = "".join([c if c.isalnum() or c in (" ", "-", "_", ".") else "_" for c in playlist_title])
        base_folder = os.path.join(opt.output_dir, safe_title)
        safe_mkdir(base_folder)
        
        self._log(f"Found {len(entries)} items. Destination: {base_folder}")
        base_cmd = self._get_common_flags(opt)

        def download_item(entry: dict, index: int) -> int:
            if self._stop_requested: return 1
            url = entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}"
            title = entry.get("title", "Video")
            out_file = os.path.join(base_folder, f"{index:03d} - %(title)s.%(ext)s")
            cmd = list(base_cmd) + ["--no-playlist", "-o", out_file, url]
            self._log(f"[{index:03d}] Queuing: {title}")
            return self._run_cmd(cmd)

        with concurrent.futures.ThreadPoolExecutor(max_workers=opt.workers) as executor:
            futures = []
            for i, entry in enumerate(entries, start=1):
                if self._stop_requested: break
                idx = entry.get("playlist_index") or i
                futures.append(executor.submit(download_item, entry, idx))
            concurrent.futures.wait(futures)
            
        self._log("Parallel download finished.")
        return 0

    def run(self, opt: DownloadOptions) -> int:
        self._stop_requested = False
        with self._proc_lock:
             self._active_procs.clear()
        
        self.check_deps()
        resolved_type = self.probe_url_type(opt.url, opt.cookies_from_browser) if opt.mode == "auto" else opt.mode

        if resolved_type == "playlist" and opt.workers > 1:
            return self.run_parallel(opt)

        cmd = self.build_cmd(opt, resolved_type)
        self._log("Running:\n  " + " ".join(cmd) + "\n")
        
        # Compatibility with legacy self.proc
        self.proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, universal_newlines=True
        )
        self._register_proc(self.proc)
        
        assert self.proc.stdout is not None
        for line in self.proc.stdout:
            if self._stop_requested:
                self.proc.terminate()
                break
            self._log(line.rstrip("\n"))

        rc = self.proc.wait()
        self._unregister_proc(self.proc)
        return rc
