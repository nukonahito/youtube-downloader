#!/usr/bin/env bash
# 配布用 ZIP を作成し、個人情報・不要ファイルが含まれていないことを検査する。
#
# GitHub の "Download ZIP" は実質 git archive と同じ内容になるため、
# ここで作る ZIP を検査することは、友人が実際に受け取る ZIP を検査することと
# ほぼ同義になる。
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

OUT_DIR="$REPO_ROOT/dist"
ZIP_PATH="$OUT_DIR/youtube-downloader.zip"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

mkdir -p "$OUT_DIR"
rm -f "$ZIP_PATH"

echo "== git archive で配布物を作成 =="
git archive --format=zip --prefix=youtube-downloader/ HEAD -o "$ZIP_PATH"

echo
echo "== 展開して検査 =="
unzip -q "$ZIP_PATH" -d "$WORK_DIR"

FAIL=0

echo
echo "-- 不要ファイル/ディレクトリの混入チェック --"
FORBIDDEN_NAMES=(".venv" "__pycache__" ".DS_Store" "__MACOSX" ".pytest_cache")
for name in "${FORBIDDEN_NAMES[@]}"; do
  hits="$(find "$WORK_DIR" -name "$name" 2>/dev/null)"
  if [ -n "$hits" ]; then
    echo "[NG] 含まれてはいけないファイル/ディレクトリが見つかりました: $name"
    echo "$hits" | sed 's/^/       /'
    FAIL=1
  fi
done
if [ "$FAIL" -eq 0 ]; then
  echo "[OK] 不要ファイルは含まれていません。"
fi

echo
echo "-- 個人情報スキャン --"
if ! "$REPO_ROOT/scripts/check_leaks.sh" "$WORK_DIR"; then
  FAIL=1
fi

echo
if [ "$FAIL" -ne 0 ]; then
  echo "検査に失敗したため ZIP を削除します: $ZIP_PATH"
  rm -f "$ZIP_PATH"
  exit 1
fi

echo "検査に合格しました: $ZIP_PATH"
