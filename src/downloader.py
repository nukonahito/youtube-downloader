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
        self.skipped_count = 0

    def _check(self, msg: str) -> None:
        if ARCHIVE_SKIP_MARKER in msg:
            self.skipped_count += 1

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
    """1 件をダウンロードし、結果を Result で返す（例外は投げない）。

    playlist/channel は 1 回の download() 呼び出しの中で何十〜何百件も処理されうる。
    アーカイブ済みスキップが1件でも混ざると全体を "skipped" と誤報しないよう、
    progress_hooks で実際にダウンロードされた件数を別途数える。
    """
    logger = _CaptureLogger(verbose)
    downloaded_ids: set[str] = set()

    def _on_progress(d: dict[str, Any]) -> None:
        if d.get("status") == "finished":
            vid = d.get("info_dict", {}).get("id")
            if vid:
                downloaded_ids.add(vid)

    ydl_opts = {
        **opts,
        "logger": logger,
        "progress_hooks": [*opts.get("progress_hooks", []), _on_progress],
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([target.url])
    except yt_dlp.utils.DownloadError as e:
        return Result(target.label, "error", str(e))
    except Exception as e:  # noqa: BLE001 - CLI境界で全て捕捉しサマリに載せる
        return Result(target.label, "error", f"{type(e).__name__}: {e}")

    if downloaded_ids:
        if logger.skipped_count:
            return Result(
                target.label,
                "ok",
                f"完了（新規 {len(downloaded_ids)}件 / 既存スキップ {logger.skipped_count}件）",
            )
        return Result(target.label, "ok", "完了")
    if logger.skipped_count:
        return Result(target.label, "skipped", "既にダウンロード済み（アーカイブ台帳）")
    return Result(target.label, "ok", "完了")


def list_formats(target: Target, opts: dict[str, Any], *, verbose: bool = False) -> Result:
    """フォーマット一覧を stdout に表示するだけで、ダウンロードは行わない。

    cookies / playlist_items 等を download_one と同じ opts で受け取る
    （以前は listformats 専用の最小 opts を自前で組んでおり、
    --cookies-from-browser や --items が無視されていた）。
    """
    ydl_opts = {**opts, "listformats": True, "quiet": not verbose}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([target.url])
    except yt_dlp.utils.DownloadError as e:
        return Result(target.label, "error", str(e))
    except Exception as e:  # noqa: BLE001
        return Result(target.label, "error", f"{type(e).__name__}: {e}")
    return Result(target.label, "ok", "一覧表示")
