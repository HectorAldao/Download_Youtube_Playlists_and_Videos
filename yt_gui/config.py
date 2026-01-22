from dataclasses import dataclass

@dataclass
class DownloadOptions:
    url: str
    output_dir: str
    mode: str  # "auto" | "playlist" | "video"
    audio_only: bool
    audio_format: str
    subtitles: bool
    subs_langs: str
    embed_metadata: bool
    download_archive: str  # empty means none
    cookies_from_browser: str  # empty means none
    workers: int = 1  # 1 means sequential
