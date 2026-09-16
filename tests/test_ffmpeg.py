from pathlib import Path

from src.ffmpeg import find_ffmpeg


class TestFindFfmpeg:
    def test_found_on_path(self):
        result = find_ffmpeg(which=lambda name: "/usr/bin/ffmpeg")
        assert result == Path("/usr/bin/ffmpeg")

    def test_not_found_anywhere(self, monkeypatch):
        monkeypatch.setattr("src.ffmpeg.PROJECT_ROOT", Path("/nonexistent-root"))
        result = find_ffmpeg(which=lambda name: None)
        assert result is None

    def test_falls_back_to_project_local_bin(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.ffmpeg.PROJECT_ROOT", tmp_path)
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        local_ffmpeg = bin_dir / "ffmpeg"
        local_ffmpeg.write_text("#!/bin/sh\n")
        result = find_ffmpeg(which=lambda name: None)
        assert result == local_ffmpeg

    def test_which_takes_priority_over_local_bin(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.ffmpeg.PROJECT_ROOT", tmp_path)
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        (bin_dir / "ffmpeg").write_text("#!/bin/sh\n")
        result = find_ffmpeg(which=lambda name: "/usr/bin/ffmpeg")
        assert result == Path("/usr/bin/ffmpeg")
