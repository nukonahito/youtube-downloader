#!/usr/bin/env bash
# 指定ディレクトリ（既定: このリポジトリ）を、個人情報らしき文字列について走査する。
#
# 重要: 検査パターンをこのファイルに直接書かない。パターン自体（本名・メールアドレス等）
# をコミットしたら、それ自体が漏洩になるため、実行時に環境から動的に導出する。
#
# 使い方:
#   scripts/check_leaks.sh [対象ディレクトリ]
set -uo pipefail

TARGET="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
FOUND=0

echo "検査対象: $TARGET"
echo

# --- 実行時に導出する動的パターン ---
DYNAMIC_PATTERNS=()

local_user="$(basename "$HOME")"
[ -n "$local_user" ] && DYNAMIC_PATTERNS+=("$local_user")

if command -v git >/dev/null 2>&1; then
  gname="$(git config --global user.name 2>/dev/null || true)"
  gmail="$(git config --global user.email 2>/dev/null || true)"
  [ -n "$gname" ] && DYNAMIC_PATTERNS+=("$gname")
  [ -n "$gmail" ] && DYNAMIC_PATTERNS+=("$gmail")
fi

hn="$(hostname 2>/dev/null || true)"
[ -n "$hn" ] && DYNAMIC_PATTERNS+=("$hn")

for pat in "${DYNAMIC_PATTERNS[@]}"; do
  hits="$(grep -rIl -F -- "$pat" "$TARGET" 2>/dev/null | grep -v '/\.git/')"
  if [ -n "$hits" ]; then
    echo "[NG] 動的パターン一致: \"$pat\""
    echo "$hits" | sed 's/^/       /'
    FOUND=1
  fi
done

# --- 静的な構造パターン（本名・メール自体は含まない、形の一致のみ） ---
STATIC_PATTERNS=(
  '/Users/[^/[:space:]"]+'
  'C:\\\\Users\\\\[^\\\\[:space:]"]+'
  '/Volumes/[^/[:space:]"]+'
  '/home/[^/[:space:]"]+'
  '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
  'KIOXIA'
)

for pat in "${STATIC_PATTERNS[@]}"; do
  hits="$(grep -rIlE -- "$pat" "$TARGET" 2>/dev/null | grep -v '/\.git/')"
  if [ -n "$hits" ]; then
    echo "[NG] 構造パターン一致: $pat"
    echo "$hits" | sed 's/^/       /'
    FOUND=1
  fi
done

echo
if [ "$FOUND" -ne 0 ]; then
  echo "個人情報らしき文字列が見つかりました。配布前に確認・修正してください。"
  exit 1
fi

echo "個人情報らしき文字列は見つかりませんでした。"
exit 0
