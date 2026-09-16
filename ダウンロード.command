#!/usr/bin/env bash
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [ ! -d "$DIR/.venv" ]; then
  echo "初回セットアップが未実行です。" >&2
  echo "先に「セットアップ.command」を実行してください（右クリック→「開く」）。" >&2
  read -r -p "Enter キーを押すと閉じます..." _
  exit 2
fi

source "$DIR/.venv/bin/activate"
python -m src.cli --interactive
