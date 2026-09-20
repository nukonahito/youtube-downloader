"""yt-dlp に渡すオプション dict を組み立てる純関数群。

yt_dlp のインポートはしない（テストがネットワーク/バイナリ非依存になるように）。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.targets import Target

RATE_RE = re.compile(r"^([\d.]+)\s*([KMG]?)$", re.IGNORECASE)
_RATE_MULTIPLIERS = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3}

# yt-dlp 本体の CLI（yt_dlp/__init__.py の parse_options）が --cookies-from-browser
# の "BROWSER[+KEYRING][:PROFILE][::CONTAINER]" 構文をタプルへ変換する処理と同一の正規表現。
# YoutubeDL の Python API 自体はこの文字列構文を解釈しない（生のタプルを要求する）ため、
# ここで複製しないと Profile 指定（例: "brave:Profile 1"）が黙って無視されてしまう。
_COOKIES_FROM_BROWSER_RE = re.compile(
    r"""(?x)
    (?P<name>[^+:]+)
    (?:\s*\+\s*(?P<keyring>[^:]+))?
    (?:\s*:\s*(?!:)(?P<profile>.+?))?
    (?:\s*::\s*(?P<container>.+))?
    """
)


def parse_cookies_from_browser(spec: str) -> tuple[str, str | None, str | None, str | None]:
    """"BROWSER[+KEYRING][:PROFILE][::CONTAINER]" を YoutubeDL 用タプルへ変換する。"""
    mobj = _COOKIES_FROM_BROWSER_RE.fullmatch(spec)
    if mobj is None:
        raise ValueError(f"--cookies-from-browser の指定が不正です: {spec!r}")
    name, keyring, profile, container = mobj.group("name", "keyring", "profile", "container")
    return name.lower(), profile, keyring.upper() if keyring else None, container

# .60B / .100B はバイト長トリム。Windows の MAX_PATH(260) に収まるよう
# Mac 版（.120B/.80B）より短めに揃えている（全 OS 共通のテンプレートにするため）。
OUTTMPL_VIDEO = "%(uploader).60B/%(upload_date>%Y-%m-%d)s_%(title).100B [%(id)s].%(ext)s"
OUTTMPL_SHORT = "%(uploader).60B/Shorts/%(upload_date>%Y-%m-%d)s_%(title).100B [%(id)s].%(ext)s"
# playlist_uploader（プレイリストの持ち主）を使う。uploader だと動画ごとの
# アップロード主体（コラボ・他チャンネル投稿）で変わり、同一プレイリストが
# 複数チャンネルフォルダへ分裂してしまう。
OUTTMPL_PLAYLIST = "%(playlist_uploader).60B/%(playlist_title).60B/%(playlist_index)03d_%(title).100B [%(id)s].%(ext)s"


def parse_rate(value: str) -> int:
    """"5M" / "500K" / "1G" / "1024" のような文字列をバイト数に変換する。"""
    m = RATE_RE.match(value.strip())
    if not m:
        raise ValueError(f"レート指定の形式が不正です（例: 5M, 500K, 1024): {value!r}")
    num = float(m.group(1))
    mult = _RATE_MULTIPLIERS[m.group(2).upper()]
    return int(num * mult)


def build_format(quality: str | int, audio_only: bool) -> str:
    if audio_only:
        return "bestaudio[ext=m4a]/bestaudio/best"
    if str(quality).lower() == "best":
        return "bv*+ba/b"
    height = int(quality)
    return (
        f"bv*[height<={height}][ext=mp4]+ba[ext=m4a]"
        f"/bv*[height<={height}]+ba"
        f"/b[height<={height}]"
        f"/b"
    )


def build_outtmpl(target: Target) -> str:
    if target.kind == "playlist":
        return OUTTMPL_PLAYLIST
    # --tab shorts で解決したチャンネルURL（.../shorts）は kind="channel" のまま
    # （ignoreerrors を維持するため kind は変えない）だが、保存先は単体ショート
    # と同じ Shorts/ 配下に揃える。
    if target.kind == "short" or target.url.rstrip("/").endswith("/shorts"):
        return OUTTMPL_SHORT
    return OUTTMPL_VIDEO


def build_options(
    target: Target,
    output_dir: Path,
    *,
    quality: str | int = "1080",
    audio_only: bool = False,
    embed_thumbnail: bool = True,
    embed_chapters: bool = True,
    write_info_json: bool = True,
    subtitle_langs: list[str] | None = None,
    archive_path: Path | str | None = None,
    expand_playlist: bool = False,
    playlist_items: str | None = None,
    cookies_from_browser: str | None = None,
    cookies_file: Path | str | None = None,
    limit_rate: int | None = None,
    ignore_playlist_errors: bool = True,
    verbose: bool = False,
    ffmpeg_location: Path | str | None = None,
) -> dict[str, Any]:
    """1 件の Target について yt_dlp.YoutubeDL に渡す opts dict を作る。"""
    opts: dict[str, Any] = {
        "format": build_format(quality, audio_only),
        "outtmpl": {"default": str(Path(output_dir) / build_outtmpl(target))},
        "writethumbnail": embed_thumbnail,
        "writeinfojson": write_info_json,
        "retries": 10,
        "fragment_retries": 10,
        "concurrent_fragment_downloads": 4,
        "continuedl": True,
        "live_from_start": target.kind == "live",
        "quiet": not verbose,
        "no_warnings": not verbose,
        # ファイル名から Windows で禁止された文字（\ / : * ? " < > |）を除去する。
        # 全 OS で常時有効にすることで、外付けドライブが exFAT でも安全にする。
        "windowsfilenames": True,
    }

    if ffmpeg_location:
        # ディレクトリではなくバイナリのフルパスを渡す。yt-dlp 側がこれを見て
        # 兄弟の ffprobe / ffprobe.exe を拡張子込みで正しく解決する。
        opts["ffmpeg_location"] = str(ffmpeg_location)

    if not audio_only:
        opts["merge_output_format"] = "mp4"

    if target.kind in {"video", "short", "live"}:
        # list= 付きの watch URL でも既定では単一動画のみ（--playlist で反転）。
        opts["noplaylist"] = not expand_playlist

    if target.kind in {"playlist", "channel"}:
        opts["ignoreerrors"] = "only_download" if ignore_playlist_errors else False

    if playlist_items:
        opts["playlist_items"] = playlist_items

    if archive_path:
        opts["download_archive"] = str(archive_path)

    if cookies_from_browser:
        opts["cookiesfrombrowser"] = parse_cookies_from_browser(cookies_from_browser)

    if cookies_file:
        opts["cookiefile"] = str(cookies_file)

    if limit_rate:
        opts["ratelimit"] = limit_rate

    if subtitle_langs:
        opts["writesubtitles"] = True
        opts["writeautomaticsub"] = True
        opts["subtitleslangs"] = list(subtitle_langs)

    postprocessors: list[dict[str, Any]] = []
    if audio_only:
        postprocessors.append({"key": "FFmpegExtractAudio", "preferredcodec": "m4a"})
    if embed_chapters:
        postprocessors.append({"key": "FFmpegMetadata", "add_chapters": True, "add_metadata": True})
    if embed_thumbnail:
        postprocessors.append({"key": "EmbedThumbnail"})
    if subtitle_langs:
        postprocessors.append({"key": "FFmpegEmbedSubtitle"})
    opts["postprocessors"] = postprocessors

    return opts
