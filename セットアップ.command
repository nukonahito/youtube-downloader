#!/usr/bin/env bash
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python3 が見つかりません。" >&2
  echo "https://www.python.org/downloads/ から Python 3.10 以上をインストールしてから" >&2
  echo "もう一度実行してください。" >&2
  read -r -p "Enter キーを押すと閉じます..." _
  exit 1
fi

python3 -m src.setup_wizard
rc=$?
echo
read -r -p "Enter キーを押すと閉じます..." _
exit $rc
