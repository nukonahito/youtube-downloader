"""入力（URL または動画/プレイリスト ID）を yt-dlp に渡せる形へ正規化する。

ネットワークアクセスも CLI 引数への依存もない純関数のみを置く。
"""
from __future__ import annotations

import re
from typing import NamedTuple
from urllib.parse import parse_qs, urlparse

# yt-dlp の動画 ID は base64url 相当の 11 文字（[A-Za-z0-9_-]）固定。
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

# プレイリスト ID の代表的な接頭辞（PL=通常, UU=チャンネルのアップロード全体,
# OL=ミックス/アルバム, FL=お気に入り, RD=Mix, LL=後で見る）。
PLAYLIST_ID_RE = re.compile(r"^(PL|UU|OL|FL|RD|LL)[A-Za-z0-9_-]{10,}$")

YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
}
YOUTU_BE_HOSTS = {"youtu.be", "www.youtu.be"}

KINDS = ("video", "short", "live", "playlist", "channel", "other")

TAB_SUFFIX = {
    "videos": "/videos",
    "shorts": "/shorts",
    "live": "/streams",
    "all": "",
}


class Target(NamedTuple):
    url: str
    kind: str  # KINDS のいずれか
    label: str  # 進捗表示用の短い識別子（動画ID・プレイリストID・ハンドル名など）


def normalize(raw: str) -> Target:
    """URL または ID の文字列 1 件を Target に正規化する。

    認識できない裸トークン（ID のつもりだが長さ/形式が合わないもの）は
    ValueError を投げる。YouTube 以外のドメインや未知の YouTube パスは
    kind="other" としてそのまま yt-dlp に渡す（yt-dlp が対応していれば通る）。
    """
    raw = raw.strip()
    if not raw:
        raise ValueError("空の入力です")

    if raw.startswith("@"):
        return Target(url=f"https://www.youtube.com/{raw}", kind="channel", label=raw)

    if VIDEO_ID_RE.match(raw):
        return Target(url=f"https://www.youtube.com/watch?v={raw}", kind="video", label=raw)

    if PLAYLIST_ID_RE.match(raw):
        return Target(url=f"https://www.youtube.com/playlist?list={raw}", kind="playlist", label=raw)

    first_segment = raw.split("/", 1)[0]
    looks_like_domain = "://" in raw or "." in first_segment
    if not looks_like_domain:
        raise ValueError(
            f"認識できない入力です（動画/プレイリストIDは11文字以上の英数字、"
            f"またはYouTubeのURLを指定してください）: {raw!r}"
        )

    url = raw if "://" in raw else f"https://{raw}"
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    query = parse_qs(parsed.query)
    segments = [s for s in parsed.path.split("/") if s]

    if host in YOUTU_BE_HOSTS:
        vid = segments[0] if segments else ""
        if VIDEO_ID_RE.match(vid):
            return Target(url=f"https://www.youtube.com/watch?v={vid}", kind="video", label=vid)
        return Target(url=url, kind="other", label=raw)

    if host not in YOUTUBE_HOSTS:
        return Target(url=url, kind="other", label=raw)

    if segments and segments[0] == "watch":
        v = query.get("v", [None])[0]
        lst = query.get("list", [None])[0]
        if v and VIDEO_ID_RE.match(v):
            # list= が付いていても既定では単一動画として扱う（--playlist で反転）。
            return Target(url=url, kind="video", label=v)
        if lst:
            return Target(url=f"https://www.youtube.com/playlist?list={lst}", kind="playlist", label=lst)
        return Target(url=url, kind="other", label=raw)

    if segments and segments[0] == "shorts" and len(segments) >= 2:
        vid = segments[1]
        return Target(url=f"https://www.youtube.com/shorts/{vid}", kind="short", label=vid)

    if segments and segments[0] == "live" and len(segments) >= 2:
        vid = segments[1]
        return Target(url=f"https://www.youtube.com/live/{vid}", kind="live", label=vid)

    if segments and segments[0] == "embed" and len(segments) >= 2:
        vid = segments[1]
        return Target(url=f"https://www.youtube.com/watch?v={vid}", kind="video", label=vid)

    if segments and segments[0] == "playlist":
        lst = query.get("list", [None])[0]
        if lst:
            return Target(url=f"https://www.youtube.com/playlist?list={lst}", kind="playlist", label=lst)
        return Target(url=url, kind="other", label=raw)

    if segments and segments[0] in {"channel", "c", "user"} and len(segments) >= 2:
        base = f"https://www.youtube.com/{segments[0]}/{segments[1]}"
        return Target(url=base, kind="channel", label=segments[1])

    if segments and segments[0].startswith("@"):
        return Target(url=f"https://www.youtube.com/{segments[0]}", kind="channel", label=segments[0])

    return Target(url=url, kind="other", label=raw)


def resolve_channel_url(url: str, tab: str = "videos") -> str:
    """チャンネルの基底 URL に --tab で指定されたタブを付与する。"""
    suffix = TAB_SUFFIX.get(tab, TAB_SUFFIX["videos"])
    base = url.rstrip("/")
    return f"{base}{suffix}" if suffix else base
