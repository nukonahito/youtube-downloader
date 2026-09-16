from pathlib import Path

from src.config import DEFAULT_CONFIG, default_output_dir, load_config, resolve_output_dir


class TestDefaultOutputDir:
    def test_mac_uses_movies(self, monkeypatch):
        monkeypatch.setattr("src.config.sys.platform", "darwin")
        assert default_output_dir() == Path.home() / "Movies" / "YouTube"

    def test_windows_uses_videos(self, monkeypatch):
        monkeypatch.setattr("src.config.sys.platform", "win32")
        assert default_output_dir() == Path.home() / "Videos" / "YouTube"

    def test_linux_uses_videos(self, monkeypatch):
        monkeypatch.setattr("src.config.sys.platform", "linux")
        assert default_output_dir() == Path.home() / "Videos" / "YouTube"


class TestLoadConfig:
    def test_missing_file_returns_defaults(self, tmp_path):
        cfg = load_config(tmp_path / "nonexistent.toml")
        assert cfg == DEFAULT_CONFIG

    def test_partial_override_merges_with_defaults(self, tmp_path):
        toml_path = tmp_path / "config.toml"
        toml_path.write_text('[download]\nquality = 720\n', encoding="utf-8")
        cfg = load_config(toml_path)
        assert cfg["download"]["quality"] == 720
        # 上書きしていないキーは既定値のまま残る
        assert cfg["output"]["fallback_dir"] == DEFAULT_CONFIG["output"]["fallback_dir"]

    def test_example_config_loads(self):
        # 配布物に同梱する config.example.toml がパースできることの確認。
        # config.toml は個人設定のため配布物に含まれず、環境によって有無が変わるので
        # 常に存在する example 側を検証対象にする。
        example_path = Path(__file__).resolve().parent.parent / "config.example.toml"
        cfg = load_config(example_path)
        assert "external_drive" in cfg["output"]


class TestResolveOutputDir:
    def test_cli_arg_wins(self):
        out, fallback = resolve_output_dir(cli_output_dir="/tmp/explicit", config={})
        assert out == Path("/tmp/explicit")
        assert fallback is False

    def test_env_var_used_when_no_cli_arg(self):
        out, fallback = resolve_output_dir(env_output_dir="/tmp/from-env", config={})
        assert out == Path("/tmp/from-env")
        assert fallback is False

    def test_cli_arg_beats_env_var(self):
        out, _ = resolve_output_dir(cli_output_dir="/tmp/cli", env_output_dir="/tmp/env", config={})
        assert out == Path("/tmp/cli")

    def test_external_drive_used_when_available(self):
        cfg = {"output": {"external_drive": "/Volumes/FAKE/YouTube", "fallback_dir": "/tmp/fallback"}}
        out, fallback = resolve_output_dir(config=cfg, is_available=lambda p: True)
        assert out == Path("/Volumes/FAKE/YouTube")
        assert fallback is False

    def test_fallback_used_when_external_drive_unavailable(self):
        cfg = {"output": {"external_drive": "/Volumes/FAKE/YouTube", "fallback_dir": "~/Movies/YouTube"}}
        out, fallback = resolve_output_dir(config=cfg, is_available=lambda p: False)
        assert out == Path("~/Movies/YouTube").expanduser()
        assert fallback is True

    def test_no_external_drive_configured_goes_to_fallback(self):
        cfg = {"output": {"fallback_dir": "/tmp/fallback"}}
        out, fallback = resolve_output_dir(config=cfg)
        assert out == Path("/tmp/fallback")
        assert fallback is True

    def test_no_fallback_configured_uses_os_default(self, monkeypatch):
        monkeypatch.setattr("src.config.sys.platform", "darwin")
        cfg = {"output": {}}
        out, fallback = resolve_output_dir(config=cfg)
        assert out == Path.home() / "Movies" / "YouTube"
        assert fallback is True


class TestIsExternalDriveAvailable:
    def test_parent_exists_is_available(self, tmp_path):
        from src.config import _is_external_drive_available

        (tmp_path / "mounted").mkdir()
        assert _is_external_drive_available(tmp_path / "mounted" / "YouTube") is True

    def test_parent_missing_is_unavailable(self, tmp_path):
        from src.config import _is_external_drive_available

        assert _is_external_drive_available(tmp_path / "not-mounted" / "YouTube") is False
