"""ffmpeg の実体を探す。

yt-dlp のマージ（映像+音声）・サムネイル/チャプター埋め込みには ffmpeg/ffprobe が
必要。PATH 上になければ、プロジェクト内 bin/（セットアップウィザードが置く場合）、
次に ffmpeg-downloader パッケージ（自動導入の最終手段）の順で探す。
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Callable, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _ffmpeg_binary_name() -> str:
    return "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"


def find_ffmpeg(*, which: Callable[[str], Optional[str]] = shutil.which) -> Path | None:
    """ffmpeg 実行ファイルのフルパスを返す。見つからなければ None。

    yt-dlp には（ディレクトリではなく）*バイナリのフルパス* を渡す。そうすると
    yt-dlp 側が兄弟の ffprobe / ffprobe.exe を拡張子込みで正しく解決できる。
    """
    on_path = which("ffmpeg")
    if on_path:
        return Path(on_path)

    local = PROJECT_ROOT / "bin" / _ffmpeg_binary_name()
    if local.is_file():
        return local

    try:
        import ffmpeg_downloader as ffdl  # セットアップ時に導入されていれば使う
    except ImportError:
        return None

    path = getattr(ffdl, "ffmpeg_path", None)
    if path and Path(path).is_file():
        return Path(path)
    return None
