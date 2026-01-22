#!/usr/bin/env python3
"""
YouTube Playlist / Single Video Downloader (GUI) using yt-dlp.
"""

import sys
import os

# Ensure the current directory is in sys.path so we can import the package
# if running strictly as a script in some environments
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from yt_gui.gui import main_gui

if __name__ == "__main__":
    sys.exit(main_gui())

