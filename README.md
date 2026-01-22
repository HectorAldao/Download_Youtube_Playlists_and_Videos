# YouTube Playlist Downloader

Download YouTube videos and playlists.

## Requirements

- **Python 3.7+**
- **yt-dlp**: The core downloading engine.
- **ffmpeg**: Required for audio conversion and merging video streams.

## Installation

1.  **Clone**
    ```sh
    git clone https://github.com/your-username/ytmp3_playlist.git
    cd ytmp3_playlist
    ```

2.  **Python dependencies**
    ```bash
    pip install -U yt-dlp
    ```

3.  **FFmpeg:**
    - **Debian/Ubuntu/Mint:** `sudo apt install ffmpeg`
    - **Arch Linux/Manjaro:** `sudo pacman -S ffmpeg`
    - **Fedora/RHEL:** `sudo dnf install ffmpeg` (requires RPM Fusion on some versions)
    - **NixOS:** Add `ffmpeg` to your configuration or run `nix-env -iA nixos.ffmpeg`
    - **Gentoo:** `sudo emerge --ask media-video/ffmpeg`
    - **macOS:** `brew install ffmpeg`
    - **Windows:** Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to your system PATH.

## Usage

### Graphical User Interface (GUI)

The GUI provides a user-friendly way to configure your downloads.

Run the GUI with:
```bash
python main.py
```

To prevent re-downloading videos when new items are added to a playlist, use the download archive. The archive file stores each downloaded video ID. Create/select an archive file on the first run, then reuse the same file on subsequent runs to automatically skip already-downloaded videos. If the file already exists, you may see an “Override?” prompt, but it does not overide it.

### Command Line Interface (CLI)

For quick downloads or automation, use the CLI `main_cli.py`.

**Basic usage:**
```bash
python main_cli.py "https://www.youtube.com/playlist?list=..."
```

**Options:**
- `-o`, `--output`: Specify output folder (default: `downloads`).
- `--audio-only`: Download audio only.
- `--audio-format`: Specify format (mp3, m4a, etc.).
- `--subtitles`: Download subtitles.
- `--archive`: Use a download archive to skip already downloaded files.

**Example:**
```bash
python main_cli.py "https://youtu.be/..." --audio-only --audio-format mp3 -o ~/Music
```

## Discaimer

I've only used it in arch (btw), and with public playlists to download in mp3 format.