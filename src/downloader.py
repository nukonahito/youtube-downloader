"""yt_dlp.YoutubeDL の実行ラッパ。ネットワーク/外部プロセスに触れる唯一の場所。"""
from __future__ import annotations

from typing import Any, NamedTuple

import yt_dlp

from src.targets import Target

ARCHIVE_SKIP_MARKER = "has already been recorded in the archive"


class Result(NamedTuple):
    label: str
    status: str  # "ok" | "skipped" | "error"
    message: str


class _CaptureLogger:
    """yt-dlp のログを横取りして、アーカイブ済みスキップを検出する。"""

    def __init__(self, verbose: bool) -> None:
        self.verbose = verbose
        self.skipped = False

    def _check(self, msg: str) -> None:
        if ARCHIVE_SKIP_MARKER in msg:
            self.skipped = True

    def debug(self, msg: str) -> None:
        self._check(msg)
        if self.verbose:
            print(msg)

    def info(self, msg: str) -> None:
        self._check(msg)
        if self.verbose:
            print(msg)

    def warning(self, msg: str) -> None:
        self._check(msg)
        print(f"[warning] {msg}")

    def error(self, msg: str) -> None:
        self._check(msg)
        print(f"[error] {msg}")


def download_one(target: Target, opts: dict[str, Any], *, verbose: bool = False) -> Result:
    """1 件をダウンロードし、結果を Result で返す（例外は投げない）。"""
    logger = _CaptureLogger(verbose)
    ydl_opts = {**opts, "logger": logger}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([target.url])
    except yt_dlp.utils.DownloadError as e:
        return Result(target.label, "error", str(e))
    except Exception as e:  # noqa: BLE001 - CLI境界で全て捕捉しサマリに載せる
        return Result(target.label, "error", f"{type(e).__name__}: {e}")

    if logger.skipped:
        return Result(target.label, "skipped", "既にダウンロード済み（アーカイブ台帳）")
    return Result(target.label, "ok", "完了")


def list_formats(target: Target, *, verbose: bool = False) -> Result:
    """フォーマット一覧を stdout に表示するだけで、ダウンロードは行わない。"""
    ydl_opts: dict[str, Any] = {"listformats": True, "quiet": not verbose}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([target.url])
    except yt_dlp.utils.DownloadError as e:
        return Result(target.label, "error", str(e))
    except Exception as e:  # noqa: BLE001
        return Result(target.label, "error", f"{type(e).__name__}: {e}")
    return Result(target.label, "ok", "一覧表示")
