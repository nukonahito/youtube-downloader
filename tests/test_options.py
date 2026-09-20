from pathlib import Path

import pytest

from src.options import build_format, build_options, parse_cookies_from_browser, parse_rate
from src.targets import Target


def video_target(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"):
    return Target(url=url, kind="video", label="dQw4w9WgXcQ")


class TestBuildFormat:
    def test_default_quality(self):
        fmt = build_format("1080", audio_only=False)
        assert "height<=1080" in fmt
        assert fmt.endswith("/b")

    def test_720p(self):
        fmt = build_format("720", audio_only=False)
        assert "height<=720" in fmt

    def test_best(self):
        assert build_format("best", audio_only=False) == "bv*+ba/b"

    def test_audio_only_ignores_quality(self):
        fmt = build_format("1080", audio_only=True)
        assert "height" not in fmt
        assert "m4a" in fmt


class TestParseRate:
    def test_plain_bytes(self):
        assert parse_rate("1024") == 1024

    def test_kilobytes(self):
        assert parse_rate("500K") == 500 * 1024

    def test_megabytes(self):
        assert parse_rate("5M") == 5 * 1024 * 1024

    def test_gigabytes(self):
        assert parse_rate("1G") == 1024**3

    def test_lowercase_suffix(self):
        assert parse_rate("5m") == 5 * 1024 * 1024

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_rate("fast")


class TestParseCookiesFromBrowser:
    def test_browser_only(self):
        assert parse_cookies_from_browser("brave") == ("brave", None, None, None)

    def test_browser_with_profile(self):
        assert parse_cookies_from_browser("brave:Profile 1") == ("brave", "Profile 1", None, None)

    def test_browser_with_keyring(self):
        assert parse_cookies_from_browser("chrome+basictext") == ("chrome", None, "BASICTEXT", None)

    def test_browser_with_profile_and_container(self):
        assert parse_cookies_from_browser("firefox:default::Meta") == ("firefox", "default", None, "Meta")

    def test_uppercased_name_lowered(self):
        assert parse_cookies_from_browser("Brave") == ("brave", None, None, None)


class TestBuildOptions:
    def test_video_defaults(self):
        opts = build_options(video_target(), Path("/tmp/out"))
        assert opts["merge_output_format"] == "mp4"
        assert opts["noplaylist"] is True
        assert opts["writethumbnail"] is True
        assert opts["writeinfojson"] is True
        assert {"key": "EmbedThumbnail"} in opts["postprocessors"]
        assert any(pp["key"] == "FFmpegMetadata" for pp in opts["postprocessors"])

    def test_windowsfilenames_always_enabled(self):
        # exFAT の外付けドライブでも壊れないように、全OSで常時有効化する。
        opts = build_options(video_target(), Path("/tmp/out"))
        assert opts["windowsfilenames"] is True

    def test_ffmpeg_location_set_when_given(self):
        opts = build_options(video_target(), Path("/tmp/out"), ffmpeg_location="/opt/homebrew/bin/ffmpeg")
        assert opts["ffmpeg_location"] == "/opt/homebrew/bin/ffmpeg"

    def test_ffmpeg_location_absent_when_none(self):
        opts = build_options(video_target(), Path("/tmp/out"), ffmpeg_location=None)
        assert "ffmpeg_location" not in opts

    def test_expand_playlist_disables_noplaylist(self):
        opts = build_options(video_target(), Path("/tmp/out"), expand_playlist=True)
        assert opts["noplaylist"] is False

    def test_audio_only_drops_merge_and_video_format(self):
        opts = build_options(video_target(), Path("/tmp/out"), audio_only=True)
        assert "merge_output_format" not in opts
        assert "height" not in opts["format"]
        assert any(pp["key"] == "FFmpegExtractAudio" for pp in opts["postprocessors"])

    def test_no_thumbnail_flag(self):
        opts = build_options(video_target(), Path("/tmp/out"), embed_thumbnail=False)
        assert opts["writethumbnail"] is False
        assert {"key": "EmbedThumbnail"} not in opts["postprocessors"]

    def test_no_chapters_flag(self):
        opts = build_options(video_target(), Path("/tmp/out"), embed_chapters=False)
        assert not any(pp["key"] == "FFmpegMetadata" for pp in opts["postprocessors"])

    def test_no_info_json_flag(self):
        opts = build_options(video_target(), Path("/tmp/out"), write_info_json=False)
        assert opts["writeinfojson"] is False

    def test_archive_path_set(self):
        opts = build_options(video_target(), Path("/tmp/out"), archive_path=Path("/tmp/out/.downloaded.txt"))
        assert opts["download_archive"] == "/tmp/out/.downloaded.txt"

    def test_no_archive_when_none(self):
        opts = build_options(video_target(), Path("/tmp/out"), archive_path=None)
        assert "download_archive" not in opts

    def test_short_outtmpl_nests_shorts_under_uploader(self):
        t = Target(url="https://www.youtube.com/shorts/dQw4w9WgXcQ", kind="short", label="dQw4w9WgXcQ")
        opts = build_options(t, Path("/tmp/out"))
        assert opts["outtmpl"]["default"].startswith("/tmp/out/%(uploader)")
        assert "/Shorts/" in opts["outtmpl"]["default"]

    def test_channel_shorts_tab_uses_shorts_outtmpl(self):
        t = Target(url="https://www.youtube.com/@Yunagi_Yosuga/shorts", kind="channel", label="@Yunagi_Yosuga")
        opts = build_options(t, Path("/tmp/out"))
        assert opts["outtmpl"]["default"].startswith("/tmp/out/%(uploader)")
        assert "/Shorts/" in opts["outtmpl"]["default"]

    def test_channel_videos_tab_uses_video_outtmpl(self):
        t = Target(url="https://www.youtube.com/@Yunagi_Yosuga/videos", kind="channel", label="@Yunagi_Yosuga")
        opts = build_options(t, Path("/tmp/out"))
        assert "/Shorts/" not in opts["outtmpl"]["default"]

    def test_playlist_outtmpl_has_playlist_index(self):
        t = Target(url="https://www.youtube.com/playlist?list=PLxxx", kind="playlist", label="PLxxx")
        opts = build_options(t, Path("/tmp/out"))
        assert "playlist_index" in opts["outtmpl"]["default"]
        assert "noplaylist" not in opts

    def test_playlist_sets_ignoreerrors(self):
        t = Target(url="https://www.youtube.com/playlist?list=PLxxx", kind="playlist", label="PLxxx")
        opts = build_options(t, Path("/tmp/out"))
        assert opts["ignoreerrors"] == "only_download"

    def test_subtitle_langs_enable_embedding(self):
        opts = build_options(video_target(), Path("/tmp/out"), subtitle_langs=["ja", "en"])
        assert opts["writesubtitles"] is True
        assert opts["subtitleslangs"] == ["ja", "en"]
        assert any(pp["key"] == "FFmpegEmbedSubtitle" for pp in opts["postprocessors"])

    def test_no_subtitle_langs_by_default(self):
        opts = build_options(video_target(), Path("/tmp/out"))
        assert "writesubtitles" not in opts

    def test_live_kind_sets_live_from_start(self):
        t = Target(url="https://www.youtube.com/live/dQw4w9WgXcQ", kind="live", label="dQw4w9WgXcQ")
        opts = build_options(t, Path("/tmp/out"))
        assert opts["live_from_start"] is True

    def test_cookies_from_browser(self):
        opts = build_options(video_target(), Path("/tmp/out"), cookies_from_browser="chrome")
        assert opts["cookiesfrombrowser"] == ("chrome", None, None, None)

    def test_cookies_from_browser_with_profile(self):
        opts = build_options(video_target(), Path("/tmp/out"), cookies_from_browser="brave:Profile 1")
        assert opts["cookiesfrombrowser"] == ("brave", "Profile 1", None, None)

    def test_cookies_file(self):
        opts = build_options(video_target(), Path("/tmp/out"), cookies_file="/tmp/cookies.txt")
        assert opts["cookiefile"] == "/tmp/cookies.txt"

    def test_no_cookies_file_when_none(self):
        opts = build_options(video_target(), Path("/tmp/out"))
        assert "cookiefile" not in opts

    def test_limit_rate(self):
        opts = build_options(video_target(), Path("/tmp/out"), limit_rate=5 * 1024 * 1024)
        assert opts["ratelimit"] == 5 * 1024 * 1024

    def test_playlist_items(self):
        opts = build_options(video_target(), Path("/tmp/out"), playlist_items="1-10,15")
        assert opts["playlist_items"] == "1-10,15"
