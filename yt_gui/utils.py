import os
import shutil

def which_or_none(cmd: str) -> str | None:
    return shutil.which(cmd)

def expand_path(p: str) -> str:
    return os.path.abspath(os.path.expanduser(p.strip()))

def safe_mkdir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def is_windows() -> bool:
    return os.name == "nt"
