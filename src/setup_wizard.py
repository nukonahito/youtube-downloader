"""初回セットアップウィザード。

このファイルは venv 作成前に「システムの python」から直接実行されるため、
依存パッケージ（yt-dlp 等）を一切 import しない（stdlib のみ）。また
「Python が古すぎます」というメッセージを表示する当人が、その古い Python 上で
実際に動く必要があるため、型注釈や新しい構文（PEP 604 の X | Y、match 文など）
を使わず、Python 3.6 相当の構文にとどめている。
"""
import os
import platform
import shutil
import subprocess
import sys

MIN_PYTHON = (3, 10)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_DIR = os.path.join(PROJECT_ROOT, ".venv")
REQUIREMENTS = os.path.join(PROJECT_ROOT, "requirements.txt")
CONFIG_EXAMPLE = os.path.join(PROJECT_ROOT, "config.example.toml")
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.toml")

# ZIP展開直後は実行ビットが落ちていることがあるので毎回直しておく（Windowsでは無視）。
EXECUTABLE_NAMES = (
    "ytdl",
    "セットアップ.command",
    "ダウンロード.command",
)


def _venv_python():
    if sys.platform == "win32":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python")


def _run_quiet(cmd):
    try:
        subprocess.check_call(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def check_python_version():
    if sys.version_info < MIN_PYTHON:
        print("=" * 60)
        print("Python のバージョンが古すぎます。")
        print("現在: %s" % platform.python_version())
        print("必要: Python 3.10 以上")
        print("")
        print("https://www.python.org/downloads/ から新しい Python をインストールし、")
        print("このセットアップをもう一度実行してください。")
        print("=" * 60)
        return False
    return True


def create_venv():
    if os.path.isdir(VENV_DIR):
        print("[1/5] venv は既に作成済みです。スキップします。")
        return True
    print("[1/5] venv を作成しています...")
    return subprocess.call([sys.executable, "-m", "venv", VENV_DIR]) == 0


def install_requirements():
    print("[2/5] 必要なパッケージをインストールしています（少し時間がかかります）...")
    return subprocess.call(
        [_venv_python(), "-m", "pip", "install", "-q", "-r", REQUIREMENTS]
    ) == 0


def ensure_ffmpeg():
    print("[3/5] ffmpeg を確認しています...")

    if shutil.which("ffmpeg"):
        print("      ffmpeg は既に利用可能です（PATH 上で発見）。")
        return True

    print("      ffmpeg が見つからないため、自動インストールを試みます...")

    if sys.platform == "darwin" and _run_quiet(["brew", "--version"]):
        print("      Homebrew で ffmpeg をインストールしています...")
        if _run_quiet(["brew", "install", "ffmpeg"]):
            return True

    if sys.platform == "win32" and _run_quiet(["winget", "--version"]):
        print("      winget で ffmpeg をインストールしています...")
        if _run_quiet([
            "winget", "install", "-e", "--id", "Gyan.FFmpeg",
            "--accept-source-agreements", "--accept-package-agreements",
        ]):
            return True

    print("      パッケージマネージャでの導入に失敗、または見つかりませんでした。")
    print("      ffmpeg-downloader（pip 経由の同梱版）を試します...")
    if _run_quiet([_venv_python(), "-m", "pip", "install", "-q", "ffmpeg-downloader"]):
        if _run_quiet([_venv_python(), "-m", "ffmpeg_downloader", "install", "-y"]):
            print("      ffmpeg-downloader での導入に成功しました。")
            return True

    print("")
    print("      ffmpeg の自動導入に失敗しました。以下を手動で行ってください:")
    if sys.platform == "darwin":
        print("        brew install ffmpeg")
    elif sys.platform == "win32":
        print("        winget install ffmpeg")
        print("        （winget が無い場合は https://www.gyan.dev/ffmpeg/builds/ から導入）")
    else:
        print("        お使いのパッケージマネージャで ffmpeg を導入してください")
        print("        （例: sudo apt install ffmpeg）")
    print("")
    return False


def ensure_config():
    print("[4/5] 設定ファイルを確認しています...")
    if os.path.isfile(CONFIG_PATH):
        print("      config.toml は既に存在します。スキップします。")
        return
    if os.path.isfile(CONFIG_EXAMPLE):
        shutil.copyfile(CONFIG_EXAMPLE, CONFIG_PATH)
        print("      config.example.toml から config.toml を作成しました。")


def fix_permissions():
    print("[5/5] 実行権限を確認しています...")
    if sys.platform == "win32":
        return
    for name in EXECUTABLE_NAMES:
        path = os.path.join(PROJECT_ROOT, name)
        if os.path.isfile(path):
            try:
                os.chmod(path, 0o755)
            except OSError:
                pass


def main():
    if not check_python_version():
        return 1

    print("youtube-downloader のセットアップを開始します。")
    print("")

    if not create_venv():
        print("venv の作成に失敗しました。Python が正しくインストールされているか")
        print("確認してください。")
        return 1

    if not install_requirements():
        print("パッケージのインストールに失敗しました。ネットワーク接続を確認してから")
        print("もう一度実行してください。")
        return 1

    ffmpeg_ok = ensure_ffmpeg()
    ensure_config()
    fix_permissions()

    print("")
    print("=" * 60)
    if ffmpeg_ok:
        print("セットアップが完了しました。")
    else:
        print("セットアップはほぼ完了しましたが、ffmpeg の導入だけ手動対応が必要です。")
        print("上記の手順で ffmpeg を導入してから、次に進んでください。")
    print("")
    if sys.platform == "darwin":
        print("次は「ダウンロード.command」をダブルクリックしてください。")
        print("（初回はダブルクリックだと開けないので、右クリック→「開く」を選んでください）")
    else:
        print("次は「ダウンロード.bat」をダブルクリックしてください。")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
