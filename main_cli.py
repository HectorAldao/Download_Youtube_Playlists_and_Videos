#!/usr/bin/env python3
"""
Download a YouTube playlist using yt-dlp.

Requirements:
  - Python 3
  - yt-dlp installed
  - ffmpeg installed (to merge audio/video or extract audio)

Quick Install:
  - pip install -U yt-dlp
  - (Linux) sudo apt install ffmpeg
  - (macOS) brew install ffmpeg
  - (Windows) install ffmpeg and add it to PATH

Usage:
  python main.py "https://www.youtube.com/playlist?list=XXXX"
  python main.py "URL" -o downloads
  python main.py "URL" --audio-only --audio-format mp3
"""

import argparse
import os
import shutil
import subprocess
import sys


def which_or_fail(cmd: str, help_hint: str) -> None:
    if shutil.which(cmd) is None:
        print(f"ERROR: Could not find '{cmd}' in PATH.\n{help_hint}", file=sys.stderr)
        sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download a YouTube playlist with yt-dlp.")
    parser.add_argument("url", help="Link to the YouTube playlist")
    parser.add_argument("-o", "--output", default="downloads", help="Output folder (default: downloads)")
    parser.add_argument("--audio-only", action="store_true", help="Download audio only")
    parser.add_argument("--audio-format", default="mp3", help="Audio format if --audio-only (mp3, m4a, opus...)")
    parser.add_argument("--subtitles", action="store_true", help="Download subtitles if available")
    parser.add_argument("--lang", default="en.*", help="Subtitle language (default: en.*)")
    parser.add_argument("--no-metadata", action="store_true", help="Do not embed metadata/thumbnail")
    parser.add_argument("--archive", default=None, help="File to avoid re-downloads (download archive)")
    args = parser.parse_args()

    which_or_fail("yt-dlp", "Install with: pip install -U yt-dlp (or pipx install yt-dlp)")
    which_or_fail("ffmpeg", "Install ffmpeg and ensure it is in PATH.")

    os.makedirs(args.output, exist_ok=True)

    # Template: folder by playlist title + index + title
    outtmpl = os.path.join(
        args.output,
        "%(playlist_title)s",
        "%(playlist_index)03d - %(title)s.%(ext)s",
    )

    cmd = [
        "yt-dlp",
        "--yes-playlist",
        "--ignore-errors",
        "--no-part",
        "--newline",
        "-o",
        outtmpl,
        args.url,
    ]

    if args.archive:
        cmd += ["--download-archive", args.archive]

    if not args.no_metadata:
        cmd += ["--embed-metadata", "--embed-thumbnail"]

    if args.subtitles:
        cmd += ["--write-subs", "--write-auto-subs", "--sub-langs", args.lang, "--embed-subs"]

    if args.audio_only:
        cmd += ["-x", "--audio-format", args.audio_format]

    # Note: use this only if you have rights to download this content.
    print("Running:\n  " + " ".join(cmd))
    proc = subprocess.run(cmd)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())

