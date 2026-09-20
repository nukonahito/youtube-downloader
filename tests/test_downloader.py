from __future__ import annotations

from typing import Any, Callable
from unittest.mock import patch

import yt_dlp

from src.downloader import download_one
from src.targets import Target


def _target(kind: str = "video") -> Target:
    return Target(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ", kind=kind, label="dQw4w9WgXcQ")


def _finished(video_id: str) -> Callable[[Any, list], None]:
    def _emit(logger: Any, hooks: list) -> None:
        for hook in hooks:
            hook({"status": "finished", "info_dict": {"id": video_id}})

    return _emit


def _archived(video_id: str) -> Callable[[Any, list], None]:
    def _emit(logger: Any, hooks: list) -> None:
        logger.info(f"[download] {video_id}: has already been recorded in the archive")

    return _emit


def _fake_ydl(events: list[Callable[[Any, list], None]]) -> type:
    class FakeYDL:
        def __init__(self, opts: dict[str, Any]) -> None:
            self.opts = opts

        def __enter__(self) -> "FakeYDL":
            return self

        def __exit__(self, *exc: Any) -> bool:
            return False

        def download(self, urls: list[str]) -> None:
            logger = self.opts["logger"]
            hooks = self.opts.get("progress_hooks", [])
            for event in events:
                event(logger, hooks)

    return FakeYDL


class TestDownloadOne:
    def test_single_fresh_download_is_ok(self):
        fake = _fake_ydl([_finished("dQw4w9WgXcQ")])
        with patch("src.downloader.yt_dlp.YoutubeDL", fake):
            result = download_one(_target(), {})
        assert result.status == "ok"

    def test_single_archived_item_is_skipped(self):
        fake = _fake_ydl([_archived("dQw4w9WgXcQ")])
        with patch("src.downloader.yt_dlp.YoutubeDL", fake):
            result = download_one(_target(), {})
        assert result.status == "skipped"

    def test_playlist_with_one_skip_among_many_is_ok(self):
        # 154件中153件が新規、1件だけ既存アーカイブでスキップされたケースの再現。
        # 以前は logger.skipped が bool で、1件でもスキップがあると全体を
        # "skipped" と誤報していた（153件の新規ダウンロードが握りつぶされていた）。
        events = [_finished(f"id{i}") for i in range(153)] + [_archived("id153")]
        fake = _fake_ydl(events)
        with patch("src.downloader.yt_dlp.YoutubeDL", fake):
            result = download_one(_target(kind="playlist"), {})
        assert result.status == "ok"
        assert "153" in result.message

    def test_playlist_all_skipped_is_skipped(self):
        events = [_archived("id1"), _archived("id2")]
        fake = _fake_ydl(events)
        with patch("src.downloader.yt_dlp.YoutubeDL", fake):
            result = download_one(_target(kind="playlist"), {})
        assert result.status == "skipped"

    def test_download_error_is_reported(self):
        class FakeYDL:
            def __init__(self, opts: dict[str, Any]) -> None:
                pass

            def __enter__(self) -> "FakeYDL":
                return self

            def __exit__(self, *exc: Any) -> bool:
                return False

            def download(self, urls: list[str]) -> None:
                raise yt_dlp.utils.DownloadError("boom")

        with patch("src.downloader.yt_dlp.YoutubeDL", FakeYDL):
            result = download_one(_target(), {})
        assert result.status == "error"
