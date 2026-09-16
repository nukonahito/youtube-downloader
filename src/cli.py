"""youtube-downloader の CLI 本体。

    ytdl <URL|ID> [<URL|ID> ...] [options]
"""
from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from pathlib import Path

from src import config as config_mod
from src import downloader, options, targets
from src import ffmpeg as ffmpeg_mod
from src.downloader import Result
from src.targets import Target

QUALITY_CHOICES = ["480", "720", "1080", "1440", "2160", "best"]
TAB_CHOICES = ["videos", "shorts", "live", "all"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ytdl",
        description="URL または動画/プレイリストID を渡すだけで yt-dlp でダウンロードする。",
    )
    parser.add_argument("targets", nargs="*", metavar="URL_OR_ID", help="動画/ショート/ライブ/プレイリスト/チャンネルのURLまたはID")
    parser.add_argument("-a", "--batch-file", metavar="FILE", help="1行1件のURL/IDファイル（# はコメント）")
    parser.add_argument("-o", "--output-dir", metavar="DIR", help="保存先ディレクトリ（既定: config.toml / 外付けSSD）")
    parser.add_argument("-q", "--quality", choices=QUALITY_CHOICES, default="1080", help="画質上限（既定: 1080）")
    parser.add_argument("--audio-only", action="store_true", help="音声(m4a)のみ抽出する")
    parser.add_argument("--playlist", action="store_true", dest="expand_playlist", help="watch?v=X&list=Y でプレイリスト全体を取得する（既定は単一動画）")
    parser.add_argument("--items", metavar="RANGE", help="プレイリストの範囲指定（例: 1-10,15）")
    parser.add_argument("--tab", choices=TAB_CHOICES, default="videos", help="チャンネル指定時のタブ（既定: videos）")
    parser.add_argument("--subs", nargs="?", const="ja,en", default=None, metavar="LANGS", help="字幕を取得して埋め込む（既定言語: ja,en）")
    parser.add_argument("--no-thumbnail", action="store_true", help="サムネイル埋め込みを無効化")
    parser.add_argument("--no-chapters", action="store_true", help="チャプター埋め込みを無効化")
    parser.add_argument("--no-info-json", action="store_true", help="メタデータJSON書き出しを無効化")
    parser.add_argument("--no-archive", action="store_true", help="再ダウンロード防止台帳を無効化")
    parser.add_argument("--cookies-from-browser", metavar="BROWSER", help="例: chrome, safari, firefox（メン限・年齢制限動画向け）")
    parser.add_argument("--limit-rate", metavar="RATE", help="例: 5M, 500K")
    parser.add_argument("-F", "--list-formats", action="store_true", help="フォーマット一覧のみ表示して終了")
    parser.add_argument("-n", "--dry-run", action="store_true", help="解決後のURL・保存先・オプションを表示して終了")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--update", action="store_true", help="venv内のyt-dlpを最新へ更新して終了")
    parser.add_argument("--interactive", action="store_true", help="URLを1行ずつ聞く対話モードで起動する")
    parser.add_argument("--doctor", action="store_true", help="動作環境を診断して表示する（AIに相談する際に貼り付け可能）")
    return parser


def _read_batch_file(path: str) -> list[str]:
    lines = Path(path).expanduser().read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def _run_update() -> int:
    print("yt-dlp を最新版へ更新しています...")
    proc = subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"])
    return proc.returncode


def _ffmpeg_missing_message() -> str:
    if sys.platform == "darwin":
        install = "  brew install ffmpeg"
    elif sys.platform == "win32":
        install = "  winget install ffmpeg"
    else:
        install = "  sudo apt install ffmpeg   （Debian/Ubuntu系の例。使っているディストリに合わせて）"
    return (
        "ffmpeg が見つかりません。動画と音声を1つのファイルに結合するために必要です。\n"
        "セットアップ（セットアップ.command / セットアップ.bat）をもう一度実行するか、"
        "以下を試してください:\n"
        f"{install}\n"
        "うまくいかない場合は `ytdl --doctor` の出力を AI に貼って相談してください。"
    )


def _run_doctor() -> int:
    """動作環境を診断して表示する。$HOME は ~ に置換し、ユーザー名を含めない。"""
    home = str(Path.home())

    def scrub(s: str) -> str:
        return s.replace(home, "~") if home else s

    print("=== youtube-downloader --doctor ===")
    print(f"OS: {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Python: {platform.python_version()}")

    try:
        import yt_dlp

        print(f"yt-dlp: {yt_dlp.version.__version__}")
    except Exception as e:  # noqa: BLE001
        print(f"yt-dlp: 取得できません ({type(e).__name__}: {e})")

    ffmpeg_path = ffmpeg_mod.find_ffmpeg()
    print(f"ffmpeg: {scrub(str(ffmpeg_path)) if ffmpeg_path else '見つかりません'}")

    cfg_path = config_mod.DEFAULT_CONFIG_PATH
    exists = "あり" if cfg_path.is_file() else "なし（既定値を使用）"
    print(f"config.toml: {scrub(str(cfg_path))} ({exists})")

    cfg = config_mod.load_config()
    output_dir, used_fallback = config_mod.resolve_output_dir(config=cfg)
    fallback_note = "（外付けドライブ未接続のためフォールバック）" if used_fallback else ""
    print(f"保存先: {scrub(str(output_dir))} {fallback_note}".rstrip())

    print()
    print("↑ この出力をコピーして、エラーメッセージと一緒に AI（Claude など）に貼ると")
    print("  相談しやすくなります。")
    return 0


def _read_interactive_targets() -> list[str]:
    """対話モードで URL/ID を1行ずつ読み取る（空行で入力終了）。"""
    print("YouTube の URL または動画ID を貼り付けて Enter を押してください。")
    print("複数まとめて貼ってもOK（1行1件）。何も入力せず Enter を押すと開始します。")
    lines: list[str] = []
    while True:
        print("> ", end="", flush=True)
        try:
            line = input()
        except EOFError:
            break
        if not line.strip():
            break
        lines.append(line.strip())
    return lines


def _resolve_targets(raw_targets: list[str], tab: str) -> tuple[list[Target], list[Result]]:
    resolved: list[Target] = []
    errors: list[Result] = []
    for raw in raw_targets:
        try:
            t = targets.normalize(raw)
        except ValueError as e:
            errors.append(Result(raw, "error", str(e)))
            continue
        if t.kind == "channel":
            t = t._replace(url=targets.resolve_channel_url(t.url, tab))
        resolved.append(t)
    return resolved, errors


def _summarize(results: list[Result]) -> int:
    ok = sum(1 for r in results if r.status == "ok")
    skipped = sum(1 for r in results if r.status == "skipped")
    errors = [r for r in results if r.status == "error"]
    print()
    print(f"完了 {ok} / スキップ(既取得) {skipped} / 失敗 {len(errors)}")
    for r in errors:
        print(f"  失敗: {r.label}: {r.message}")
    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.doctor:
        return _run_doctor()

    if args.update:
        return _run_update()

    # 引数もバッチファイルも無指定でターミナルから直接起動された場合
    # （ダブルクリック起動を含む）は、自動的に対話モードへ入る。
    interactive = args.interactive or (
        not args.targets and not args.batch_file and sys.stdin.isatty()
    )

    ffmpeg_path = None
    if not (args.dry_run or args.list_formats):
        ffmpeg_path = ffmpeg_mod.find_ffmpeg()
        if ffmpeg_path is None:
            print(_ffmpeg_missing_message(), file=sys.stderr)
            return 2

    raw_targets = list(args.targets)
    if args.batch_file:
        try:
            raw_targets.extend(_read_batch_file(args.batch_file))
        except OSError as e:
            print(f"エラー: バッチファイルを読み込めません: {e}", file=sys.stderr)
            return 2

    if interactive and not raw_targets:
        raw_targets = _read_interactive_targets()

    if not raw_targets:
        parser.print_usage(sys.stderr)
        print("エラー: URL/ID を1件以上指定してください（-a でファイル指定も可）。", file=sys.stderr)
        return 2

    limit_rate = None
    if args.limit_rate:
        try:
            limit_rate = options.parse_rate(args.limit_rate)
        except ValueError as e:
            print(f"エラー: {e}", file=sys.stderr)
            return 2

    cfg = config_mod.load_config()
    output_dir, used_fallback = config_mod.resolve_output_dir(cli_output_dir=args.output_dir, config=cfg)
    if used_fallback and cfg.get("output", {}).get("external_drive"):
        print(f"[警告] 外付けドライブが見つからないため保存先を {output_dir} にフォールバックします。", file=sys.stderr)
    output_dir.mkdir(parents=True, exist_ok=True)

    archive_path = None
    if not args.no_archive and cfg.get("archive", {}).get("enabled", True):
        archive_path = output_dir / cfg.get("archive", {}).get("filename", ".downloaded.txt")

    subtitle_langs = None
    if args.subs:
        subtitle_langs = [s.strip() for s in args.subs.split(",") if s.strip()]
    elif cfg.get("embed", {}).get("subtitles", False):
        subtitle_langs = cfg.get("embed", {}).get("subtitle_langs", ["ja", "en"])

    resolved, results = _resolve_targets(raw_targets, args.tab)
    total = len(resolved)

    def build_opts(t: Target) -> dict:
        return options.build_options(
            t,
            output_dir,
            quality=args.quality,
            audio_only=args.audio_only,
            embed_thumbnail=not args.no_thumbnail,
            embed_chapters=not args.no_chapters,
            write_info_json=not args.no_info_json,
            subtitle_langs=subtitle_langs,
            archive_path=archive_path,
            expand_playlist=args.expand_playlist,
            playlist_items=args.items,
            cookies_from_browser=args.cookies_from_browser,
            limit_rate=limit_rate,
            verbose=args.verbose,
            ffmpeg_location=ffmpeg_path,
        )

    if args.dry_run:
        print(f"保存先: {output_dir}")
        print(f"アーカイブ台帳: {archive_path if archive_path else '無効'}")
        for i, t in enumerate(resolved, 1):
            opts = build_opts(t)
            print(f"[{i}/{total}] {t.label} ({t.kind}) -> {t.url}")
            print(f"  format={opts['format']}")
            print(f"  outtmpl={opts['outtmpl']['default']}")
        for r in results:
            print(f"[入力エラー] {r.label}: {r.message}")
        return 1 if results else 0

    if args.list_formats:
        for i, t in enumerate(resolved, 1):
            print(f"[{i}/{total}] {t.label} ({t.kind})")
            results.append(downloader.list_formats(t, verbose=args.verbose))
        return _summarize(results)

    for i, t in enumerate(resolved, 1):
        print(f"[{i}/{total}] {t.label} ({t.kind}) を処理中...")
        r = downloader.download_one(t, build_opts(t), verbose=args.verbose)
        print(f"  -> {r.status}: {r.message}")
        results.append(r)

    exit_code = _summarize(results)

    if interactive and sys.stdin.isatty():
        # ダブルクリック起動だとウィンドウが即座に閉じてエラーが読めないため待機する。
        print()
        input("Enter キーを押すと閉じます...")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
