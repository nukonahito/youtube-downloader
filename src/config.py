"""config.toml の読み込みと保存先ディレクトリの解決。"""
from __future__ import annotations

import copy
import os
import sys
from pathlib import Path
from typing import Any, Callable

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10（tomllib は 3.11 で標準入り）
    import tomli as tomllib


def default_output_dir() -> Path:
    """外付けドライブが未設定 / 未接続のときの既定保存先。

    OS ごとの「動画」フォルダを使う（日本語 Windows でもディスク上のフォルダ名は
    Videos で、表示名だけが「ビデオ」になる）。
    """
    if sys.platform == "darwin":
        return Path.home() / "Movies" / "YouTube"
    return Path.home() / "Videos" / "YouTube"


DEFAULT_CONFIG: dict[str, Any] = {
    "output": {
        # 外付けドライブのパス。未設定（None）ならローカルディスクの既定フォルダを使う。
        # 例: "/Volumes/MyDrive/YouTube"（Mac）, "D:/YouTube"（Windows）
        "external_drive": None,
        # 未設定なら default_output_dir() を使う。
        "fallback_dir": None,
    },
    "download": {
        "quality": 1080,
        "audio_only": False,
    },
    "embed": {
        "thumbnail": True,
        "chapters": True,
        "info_json": True,
        "subtitles": False,
        "subtitle_langs": ["ja", "en"],
    },
    "archive": {
        "enabled": True,
        "filename": ".downloaded.txt",
    },
}

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.toml"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def load_config(config_path: Path | str | None = None) -> dict[str, Any]:
    """config.toml を読み込み、既定値とマージした dict を返す。

    ファイルが存在しない場合は組み込み既定値のみを返す（動作は止めない）。
    配布物には config.toml を含めない（個人の保存先設定が入るため）。
    セットアップ時に config.example.toml からコピーして作る。
    """
    data = copy.deepcopy(DEFAULT_CONFIG)
    path = Path(config_path) if config_path is not None else DEFAULT_CONFIG_PATH
    if path.is_file():
        with open(path, "rb") as f:
            loaded = tomllib.load(f)
        _deep_merge(data, loaded)
    return data


def _is_external_drive_available(path: Path) -> bool:
    """外付けドライブが現在接続されているかを判定する。

    設定パスの親ディレクトリ（マウントポイント相当）が実在するかで判定する。
    `/Volumes/<name>/YouTube` の親は `/Volumes/<name>`、`D:\\YouTube` の親は `D:\\` で、
    どちらも接続時のみ存在する。ローカルディスク上のパスなら親ディレクトリは常に
    存在するため、結果として「常に利用可能」判定になる。
    """
    return path.parent.is_dir()


def resolve_output_dir(
    *,
    cli_output_dir: str | None = None,
    env_output_dir: str | None = None,
    config: dict[str, Any] | None = None,
    is_available: Callable[[Path], bool] = _is_external_drive_available,
) -> tuple[Path, bool]:
    """保存先ディレクトリを決定する。

    優先順位: CLI 引数 > 環境変数 YTDL_OUTPUT_DIR > config.toml の external_drive
    （接続されていれば） > fallback_dir（未設定なら OS 既定の動画フォルダ）。

    戻り値は (保存先ディレクトリ, フォールバックを使ったか) のタプル。
    """
    if cli_output_dir:
        return Path(cli_output_dir).expanduser(), False

    env = env_output_dir if env_output_dir is not None else os.environ.get("YTDL_OUTPUT_DIR")
    if env:
        return Path(env).expanduser(), False

    cfg = config or DEFAULT_CONFIG
    output_cfg = cfg.get("output", {})
    external_drive = output_cfg.get("external_drive")
    fallback_dir = output_cfg.get("fallback_dir") or str(default_output_dir())

    if external_drive:
        drive_path = Path(external_drive).expanduser()
        if is_available(drive_path):
            return drive_path, False

    return Path(fallback_dir).expanduser(), True
