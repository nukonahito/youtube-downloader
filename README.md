# youtube-downloader

YouTube の **URL または動画/プレイリスト ID を渡すだけ**でダウンロードできる `yt-dlp` ラッパー。
単一動画・複数動画・プレイリスト・チャンネル・ライブアーカイブ・ショート動画のすべてに対応する。
Mac・Windows の両方で動く。

## かんたんセットアップ（IT知識がなくてもOK）

1. このフォルダをまるごと好きな場所に置く（デスクトップなど）
2. セットアップファイルを実行する
   - **Mac**: `セットアップ.command` を**右クリック →「開く」**
     （初回はダブルクリックだと「開発元を検証できません」と出て開けません。
     右クリックから「開く」を選べば実行できます。これは Apple の Gatekeeper という
     仕組みによる標準的な確認で、問題があるわけではありません）
   - **Windows**: `セットアップ.bat` を**ダブルクリック**
3. venv 作成 → 必要なパッケージのインストール → ffmpeg の自動導入 → 設定ファイル作成が
   自動で行われる。数分かかる場合がある
4. 完了したら `ダウンロード.command`（Mac）/ `ダウンロード.bat`（Windows）を実行する
5. YouTube の URL を貼り付けて Enter を押すとダウンロードが始まる

Python 自体が入っていない場合は、セットアップ実行時にインストール先の URL
（<https://www.python.org/downloads/>）が案内される。**Python 3.10 以上**が必要。
インストーラでは「Add python.exe to PATH」にチェックを入れること（Windows）。

### 手動セットアップ（開発者向け）

```bash
cd youtube-downloader
python3 -m venv .venv
source .venv/bin/activate      # Windows は .venv\Scripts\activate
pip install -r requirements.txt
cp config.example.toml config.toml
```

ffmpeg が別途必要（映像+音声のマージ・サムネイル/チャプター埋め込みに使用）。

```bash
brew install ffmpeg        # Mac
winget install ffmpeg      # Windows
```

### PATH に登録する（任意・CLI操作に慣れている人向け）

```bash
ln -s "$(pwd)/ytdl" ~/bin/ytdl   # Mac/Linux。~/bin が PATH に入っている前提
```

Windows では `ytdl.bat` があるフォルダを PATH に追加すれば `ytdl <ID>` で実行できる。

## 使い方

### 対話モード（IT知識に乏しい人向け・既定）

`ダウンロード.command` / `ダウンロード.bat` を実行する、または引数なしで `ytdl` を実行すると
対話モードに入る。

```
YouTube の URL または動画ID を貼り付けて Enter を押してください。
複数まとめて貼ってもOK（1行1件）。何も入力せず Enter を押すと開始します。
>
```

### コマンドライン（引数指定）

```bash
./ytdl dQw4w9WgXcQ                                   # 動画ID単体
./ytdl "https://www.youtube.com/watch?v=dQw4w9WgXcQ" # 動画URL
./ytdl "https://youtu.be/dQw4w9WgXcQ"                # 短縮URL
./ytdl "https://www.youtube.com/shorts/xxxxxxxxxxx"  # ショート
./ytdl "https://www.youtube.com/live/xxxxxxxxxxx"    # ライブアーカイブ
./ytdl "https://www.youtube.com/playlist?list=PLxxxx" --items 1-10
./ytdl @somechannel --tab shorts                     # チャンネルのショート一覧
./ytdl id1 id2 "https://youtu.be/id3"                # 複数まとめて
./ytdl -a urls.txt                                   # 1行1件のファイルから
```

Windows では `ytdl` の代わりに `ytdl.bat`（または単に `ytdl`）を使う。

**重要な既定動作**: `watch?v=X&list=Y` のような「プレイリスト内の1本」の URL は
**既定では単一動画のみ**をダウンロードする（プレイリスト全体を意図せず落とす事故を防ぐため）。
プレイリスト全体が欲しい場合は `--playlist` を付ける。

### 主なオプション

| オプション | 説明 |
|---|---|
| `-a, --batch-file FILE` | 1行1件のURL/IDファイルから読み込む（`#` はコメント） |
| `-o, --output-dir DIR` | 保存先を明示指定（既定は下記「保存先」参照） |
| `-q, --quality {480,720,1080,1440,2160,best}` | 画質上限（既定: 1080） |
| `--audio-only` | 音声のみ抽出（m4a） |
| `--playlist` | `list=` 付きURLでプレイリスト全体を取得する |
| `--items 1-10,15` | プレイリストの範囲指定 |
| `--tab {videos,shorts,live,all}` | チャンネル指定時に見るタブ（既定: videos） |
| `--subs [ja,en]` | 字幕を取得して埋め込む（既定OFF。値省略時は `ja,en`） |
| `--no-thumbnail` / `--no-chapters` / `--no-info-json` / `--no-archive` | 各埋め込み・台帳を無効化 |
| `--cookies-from-browser chrome` | メンバー限定・年齢制限動画向け |
| `--limit-rate 5M` | 帯域制限 |
| `-F, --list-formats` | フォーマット一覧のみ表示 |
| `-n, --dry-run` | 実行せず解決結果とオプションだけ表示 |
| `--interactive` | 対話モードを明示的に起動する |
| `--doctor` | 動作環境を診断して表示する（トラブル時にAIへ貼る用） |
| `-v, --verbose` | yt-dlp の詳細ログを表示 |
| `--update` | venv 内の yt-dlp を最新へ更新 |

終了コード: 全件成功 `0` / 一部失敗 `1` / 入力・環境エラー（ffmpeg無し・引数無し等）`2`。

## 保存先

優先順位: `-o` 指定 > 環境変数 `YTDL_OUTPUT_DIR` > `config.toml` の `external_drive`
（接続済みなら） > `fallback_dir`（未設定なら OS 既定の動画フォルダ）。

既定の保存先（`config.toml` を編集していない場合）:

- **Mac**: `~/Movies/YouTube`
- **Windows**: `~/Videos/YouTube`

外付けドライブに保存したい場合は `config.toml` の `external_drive` を設定する。
未接続の場合は自動的に `fallback_dir` へフォールバックし、その旨を警告表示する
（処理は止めない）。

```toml
[output]
external_drive = "/Volumes/YOUR-DRIVE-NAME/YouTube"   # Mac の例
# external_drive = "D:/YouTube"                        # Windows の例
fallback_dir = "~/Movies/YouTube"
```

ディレクトリ構成:
```
<保存先>/
├── .downloaded.txt              # アーカイブ台帳（再ダウンロード防止）
├── <アップロード者名>/
│   └── 2024-01-01_タイトル [動画ID].mp4  (+.info.json)
└── Shorts/<アップロード者名>/
    └── ...
```

## 再ダウンロード防止

`.downloaded.txt` に処理済みの動画IDを記録し、同じ動画を指定すると自動的にスキップする
（`スキップ(既取得)` としてサマリに表示）。`--no-archive` で無効化できる。

## テスト

```bash
source .venv/bin/activate
pytest -q
```
ネットワークを使わない純関数（URL正規化・オプション組み立て・保存先解決・ffmpeg探索）
のみを対象にしている。

## 困ったときは

1. まず `ytdl --update` で yt-dlp を最新化する（YouTube側の仕様変更が原因の失敗が多い）
2. それでも直らない場合は `ytdl --doctor` を実行し、その出力とエラーメッセージ全文を
   コピーして AI（Claude など）に貼って相談する。`--doctor` の出力にはユーザー名などの
   個人情報は含まれない（自動的に `~` に置換される）

### よくある詰まりポイント

- **Mac で `セットアップ.command` が「開発元を検証できません」で開けない**:
  ダブルクリックではなく、右クリック（または Control+クリック）→「開く」を選ぶ
- **`ffmpeg が見つかりません`**: セットアップをもう一度実行するか、
  `brew install ffmpeg`（Mac）/ `winget install ffmpeg`（Windows）を試す
- **`No supported JavaScript runtime could be found` という警告**:
  yt-dlp が YouTube 側の署名解読に JS ランタイムを使う場合があるという警告。
  無視して問題なく動作することが多いが、頻発する場合は Node.js の導入を検討する
- **急にダウンロードが失敗するようになった**: YouTube 側の仕様変更が原因のことが多い。
  `ytdl --update` で yt-dlp を最新化する
- **`--audio-only` でサムネイル埋め込みが失敗する**:
  `mutagen` が入っていないと ffmpeg 直接埋め込みにフォールバックし失敗することがある。
  `requirements.txt` に含まれているのでセットアップをやり直す

## 注意

ダウンロードは本人が視聴権を持つ範囲での私的利用を前提とする。

## License

[MIT](LICENSE)
