import pytest

from src.targets import normalize, resolve_channel_url

VIDEO_ID = "dQw4w9WgXcQ"


class TestVideo:
    def test_bare_id(self):
        t = normalize(VIDEO_ID)
        assert t.kind == "video"
        assert t.url == f"https://www.youtube.com/watch?v={VIDEO_ID}"
        assert t.label == VIDEO_ID

    def test_watch_url(self):
        t = normalize(f"https://www.youtube.com/watch?v={VIDEO_ID}")
        assert t.kind == "video"
        assert t.label == VIDEO_ID

    def test_youtu_be(self):
        t = normalize(f"https://youtu.be/{VIDEO_ID}")
        assert t.kind == "video"
        assert t.url == f"https://www.youtube.com/watch?v={VIDEO_ID}"

    def test_youtu_be_with_query(self):
        t = normalize(f"https://youtu.be/{VIDEO_ID}?t=42")
        assert t.kind == "video"
        assert t.label == VIDEO_ID

    def test_embed_url(self):
        t = normalize(f"https://www.youtube.com/embed/{VIDEO_ID}")
        assert t.kind == "video"
        assert t.url == f"https://www.youtube.com/watch?v={VIDEO_ID}"

    def test_mobile_domain(self):
        t = normalize(f"https://m.youtube.com/watch?v={VIDEO_ID}")
        assert t.kind == "video"

    def test_music_domain(self):
        t = normalize(f"https://music.youtube.com/watch?v={VIDEO_ID}")
        assert t.kind == "video"

    def test_no_scheme(self):
        t = normalize(f"www.youtube.com/watch?v={VIDEO_ID}")
        assert t.kind == "video"
        assert t.url.startswith("https://")

    def test_watch_with_list_defaults_to_single_video(self):
        """list= が付いていても既定では単一動画として扱う（--playlist で反転）。"""
        t = normalize(f"https://www.youtube.com/watch?v={VIDEO_ID}&list=PLabcdefghijklmnopqrstuvwxyz0123")
        assert t.kind == "video"
        assert t.label == VIDEO_ID
        assert "list=" in t.url  # URL自体はlist情報を保持（options側でnoplaylist制御）


class TestShort:
    def test_shorts_url(self):
        t = normalize(f"https://www.youtube.com/shorts/{VIDEO_ID}")
        assert t.kind == "short"
        assert t.label == VIDEO_ID
        assert t.url == f"https://www.youtube.com/shorts/{VIDEO_ID}"


class TestLive:
    def test_live_url(self):
        t = normalize(f"https://www.youtube.com/live/{VIDEO_ID}")
        assert t.kind == "live"
        assert t.label == VIDEO_ID


class TestPlaylist:
    def test_bare_playlist_id(self):
        pl_id = "PLabcdefghijklmnopqrstuvwxyz0123"
        t = normalize(pl_id)
        assert t.kind == "playlist"
        assert t.url == f"https://www.youtube.com/playlist?list={pl_id}"

    def test_playlist_url(self):
        pl_id = "PLabcdefghijklmnopqrstuvwxyz0123"
        t = normalize(f"https://www.youtube.com/playlist?list={pl_id}")
        assert t.kind == "playlist"
        assert t.label == pl_id

    def test_uu_uploads_playlist(self):
        pl_id = "UUabcdefghijklmnopqrstuvwx"
        t = normalize(pl_id)
        assert t.kind == "playlist"


class TestChannel:
    def test_handle_bare(self):
        t = normalize("@somechannel")
        assert t.kind == "channel"
        assert t.url == "https://www.youtube.com/@somechannel"

    def test_handle_url(self):
        t = normalize("https://www.youtube.com/@somechannel")
        assert t.kind == "channel"
        assert t.label == "@somechannel"

    def test_channel_id_url(self):
        t = normalize("https://www.youtube.com/channel/UC1234567890123456789012")
        assert t.kind == "channel"
        assert t.label == "UC1234567890123456789012"

    def test_c_url(self):
        t = normalize("https://www.youtube.com/c/SomeChannelName")
        assert t.kind == "channel"

    def test_user_url(self):
        t = normalize("https://www.youtube.com/user/SomeUser")
        assert t.kind == "channel"


class TestResolveChannelUrl:
    def test_videos_tab(self):
        assert resolve_channel_url("https://www.youtube.com/@x", "videos") == "https://www.youtube.com/@x/videos"

    def test_shorts_tab(self):
        assert resolve_channel_url("https://www.youtube.com/@x", "shorts") == "https://www.youtube.com/@x/shorts"

    def test_live_tab_maps_to_streams(self):
        assert resolve_channel_url("https://www.youtube.com/@x", "live") == "https://www.youtube.com/@x/streams"

    def test_all_tab_no_suffix(self):
        assert resolve_channel_url("https://www.youtube.com/@x", "all") == "https://www.youtube.com/@x"

    def test_trailing_slash_stripped(self):
        assert resolve_channel_url("https://www.youtube.com/@x/", "videos") == "https://www.youtube.com/@x/videos"


class TestPassthrough:
    def test_unknown_domain_passthrough(self):
        t = normalize("https://vimeo.com/12345678")
        assert t.kind == "other"
        assert t.url == "https://vimeo.com/12345678"

    def test_unknown_youtube_path_passthrough(self):
        t = normalize("https://www.youtube.com/results?search_query=test")
        assert t.kind == "other"


class TestInvalidInput:
    def test_too_short_bare_token_raises(self):
        with pytest.raises(ValueError):
            normalize("abc123defg")  # 10文字

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            normalize("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            normalize("   ")
