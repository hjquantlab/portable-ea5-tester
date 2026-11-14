# Portable Strategy Tester (`portable-ea5-tester`)

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[English](README.md) | [日本語](README.ja.md)

**Portable Strategy Tester**（`pea5`）は、MetaTrader 5 エキスパートアドバイザー（`.mq5` から `.ex5`）のコンパイル、およびバックテストや最適化の自動実行を行うための、軽量・スタンドアロン・ポータブルな CLI フレームワークです。名称の「Portable」は、ツール自体が外部依存ゼロで持ち運び可能であることに加え、**ポータブル版 MetaTrader 5（`/portable` モード）専用**であることを意味しています。

> **重要**: `portable-ea5-tester` は **`/portable` モードで動作する MetaTrader 5 専用**です。プログラム本体とデータフォルダが `%APPDATA%` に分離される通常の MT5 インストール環境には**対応していません**。

---

## 主な特徴

- **外部依存ゼロ**: Python 標準ライブラリのみで動作します（`dependencies = []`）。
- **ヘッドレス＆ポータブル実行**: JSON 設定ファイルと `pea5` CLI を通じて、MT5 のコンパイル（`metaeditor64.exe`）やバックテスト（`terminal64.exe /portable`）を自動化できます。
- **自動レポート生成**: MT5 ストラテジーテスターのレポートを解析し、`batch_summary.html` ダッシュボードの生成や、Markdown / コンパクト CSV 形式へのエクスポート（`--export`）に対応しています。

---

## 前提条件

- **OS**: Windows 10 / 11（MetaTrader 5 ターミナルおよび MetaEditor の実行に必要です）。
- **Python**: Python 3.9 以上。
- **MetaTrader 5**: `terminal64.exe` および `metaeditor64.exe` を含むポータブル版 MetaTrader 5 ディレクトリ。

---

## Step 1: ポータブル MT5 のセットアップ（3ステップ）

> **重要**: `portable-ea5-tester` は **ポータブル版 MT5（`/portable` モード）専用**であり、`%APPDATA%` にデータが分散される通常の MT5 インストール環境では動作しません。以下の手順で自己完結型のポータブル MT5 フォルダを用意してください。

1. **通常版 MetaTrader 5 をインストールする**: MetaQuotes 公式またはご利用のブローカーから MetaTrader 5 インストーラーをダウンロードし、インストールします（すでにインストール済みの場合はスキップしてください）。
2. **専用のポータブルフォルダを作成して実行ファイルをコピーする**: `C:\MT5-Portable` のような専用フォルダを作成し、通常のインストール先（例: `C:\Program Files\MetaTrader 5`）から `terminal64.exe` と `metaeditor64.exe` を `C:\MT5-Portable` にコピーします。
3. **ポータブルモードで一度起動して初期化する**: `/portable` フラグを付けて `C:\MT5-Portable\terminal64.exe` を一度起動します。
   ```powershell
   C:\MT5-Portable\terminal64.exe /portable
   ```
   これにより、`C:\MT5-Portable` 内に `MQL5/`（標準サンプル EA を含む）や `Config/` が自動的に展開されます。MT5 が起動したら一度終了し、Step 2 に進みます。

> **注意**: **初回セットアップが完了した後であっても**、`/portable` を付けずに `terminal64.exe`（または `metaeditor64.exe`）を直接ダブルクリックして起動すると、MT5 は通常モードで起動し、`C:\MT5-Portable` ではなく `%APPDATA%\MetaQuotes\Terminal\<32文字のハッシュ>\` に別フォルダを作成・参照してしまいます。誤って通常モードで起動するのを防ぐため、`C:\MT5-Portable` 内（またはデスクトップ）に `/portable` 付きショートカットを作成してそこから起動するか、`pea5 login` / `pea5 run` を使用することを推奨します（内部で自動的に `/portable` を付与します）。ショートカットの作成手順や、誤ってハッシュフォルダが作成された場合の `origin.txt` 確認・削除手順は [よくある質問（FAQ）](#よくある質問faq) を参照してください。

---

## Step 2: `portable-ea5-tester` のインストール

リポジトリをクローンし、プロジェクトディレクトリに移動します：

```powershell
git clone https://github.com/hjquantlab/portable-ea5-tester.git
cd portable-ea5-tester
```

### 方法 A: `pip` でインストールする（推奨）

仮想環境（`.venv`）を作成・有効化したうえで、外部依存ゼロの Python パッケージをローカル環境にインストールします。これにより `pea5` CLI コマンド（およびエイリアス `portable-ea5-tester` / `pst-runner`）が仮想環境内に登録されます：

- **PowerShell**:
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install .
  ```
- **コマンドプロンプト（`cmd`）**:
  ```cmd
  python -m venv .venv
  .venv\Scripts\activate.bat
  pip install .
  ```

> **補足**:
> - グローバルの Python 環境へ直接インストールしたい場合は、上記の `venv` 作成・有効化の手順を省略して直接 `pip install .` を実行してください。
> - **`uv` をご利用の場合**: `uv venv` + `uv pip install .` でインストールするか、`uv tool install .` でグローバルの CLI ツールとしてインストールすることも可能です。

開発用（`pytest` を含む）：

```powershell
pip install -e ".[dev]"
```

### 方法 B: インストールせずに試す（お試し用・一時実行 / `PYTHONPATH`）

インストールせずに手早く試したい場合は、リポジトリルート直下の `portable_ea5_tester/` を `PYTHONPATH` に `.` を設定して直接実行できます：

- **PowerShell**:
  ```powershell
  $env:PYTHONPATH = "."
  python -m portable_ea5_tester --help
  ```
- **コマンドプロンプト（`cmd`）**:
  ```cmd
  set PYTHONPATH=.
  python -m portable_ea5_tester --help
  ```

> **補足**:
> - `$env:PYTHONPATH = "."` / `set PYTHONPATH=.` の設定は **現在開いているターミナルセッション限りの一時的なもの** であり、ターミナルウィンドウを閉じるとリセットされます（新しいターミナルを開いた場合は再実行が必要です）。詳細は [よくある質問（FAQ）](#よくある質問faq) を参照してください。
> - 方法 B を使用する場合は、以降の手順にある `pea5 <サブコマンド>` を `python -m portable_ea5_tester <サブコマンド>` に読み替えてください。

---

## Step 3: ステップ・バイ・ステップ クイックスタート

### 1. 設定ファイルを作成する

サンプルテンプレートをコピーして作業用の設定ファイルを作成します：

- **PowerShell**:
  ```powershell
  Copy-Item config.example.json config.json
  Copy-Item credentials.example.json credentials.json
  ```
- **コマンドプロンプト（`cmd`）**:
  ```cmd
  copy config.example.json config.json
  copy credentials.example.json credentials.json
  ```

### 2. `config.json` と `credentials.json` を編集する

`config.example.json` は、スラッシュ `/` 区切りの Windows 絶対パス（例: `C:/MT5-Portable/terminal64.exe`）をテンプレートとして採用しています。ポータブル MT5 の配置場所が異なる場合はパスを書き換えてください。

> **JSON パス記述の注意点**:
> - Windows のパスを JSON 内に書く際、単一のバックスラッシュ `\` を使用すると JSON パースエラーになります。スラッシュ `/`（推奨、例: `"C:/MT5-Portable"`）または二重バックスラッシュ `\\`（例: `"C:\\MT5-Portable"`）を使用してください。
> - プロジェクトフォルダ内に MT5 を配置する場合は、相対パス（例: `"./mt5_terminal"`、`config.json` のあるディレクトリ基準）も指定可能です。

`credentials.json` には、MT5 口座の `login`・`password`・`server` 名を設定してください。

### 3. 動作確認テスト（疎通確認）を行う

ご自身の EA をテストする前に、MT5 標準のサンプル EA を使って環境全体が正しく動作するか一度だけ疎通確認を行います：

1. **環境の診断チェック（`pea5 init`）**:  
   **目的**: 実行前に `config.json`、MT5 の各種パス、コンパイラの検出状況を確認します。
   ```powershell
   pea5 init --config config.json
   ```
2. **MT5 にブローカー認証情報をキャッシュする（`pea5 login`）**:  
   **目的**: 自動テスト中にログイン入力画面で停止しないよう、ポータブル MT5 にブローカー認証情報を事前保存します。
   ```powershell
   pea5 login --config config.json
   ```
   口座番号とサーバーが事前入力された状態で MT5 GUI がポータブルモード起動します。必要に応じてパスワードを入力し、**「パスワードを保存」** にチェックを入れて **OK** を押し、MT5 を閉じるとコマンドが完了します。
3. **MT5 付属のサンプル EA をコンパイルする（`pea5 compile`）**:  
   **目的**: ご自身の EA をコンパイルする前に、MT5 標準サンプル EA を使って `metaeditor64.exe` によるコンパイルが正常に動作することを確認します。
   ```powershell
   pea5 compile --file "C:/MT5-Portable/MQL5/Experts/Examples/Moving Average/Moving Average.mq5" --terminal-dir C:/MT5-Portable
   ```
   > **補足**: `.mqh` インクルードパスの解決（`--include`）や、MetaEditor GUI を用いたコンパイルエラーの詳細調査については [よくある質問（FAQ）](#よくある質問faq) を参照してください。
4. **バックテストを実行し、レポートを出力する（`pea5 run`）**:  
   **目的**: ストラテジーテスターの実行からレポート出力までの一連の動作を確認します。
   ```powershell
   pea5 run --config config.json --export
   ```

---

## CLI リファレンス

| コマンド | 説明・オプション |
| :--- | :--- |
| `pea5 init [--config config.json]` | `config.json`、MT5 ターミナル・コンパイラのパス、認証情報を検証する診断ウィザード。（`-c` / `--config`、デフォルト: `config.json`） |
| `pea5 login [--config config.json]` | `Login` と `Server` を事前入力して MT5 GUI を `/portable` モードで起動し、認証情報をキャッシュします。（`--config` のデフォルトは `tester_config.json` のため、`--config config.json` の明示を推奨） |
| `pea5 compile --file <path.mq5> [options]` | MetaEditor を使用して `.mq5` を `.ex5` にコンパイルします。<br>オプション: `-f` / `--file`（必須）、`--compiler <metaeditor64.exe>`、`--terminal-dir <dir>`、`-i` / `--include <dir>`、`--timeout <秒>`（デフォルト: `60`）。 |
| `pea5 run [--config config.json] [options]` | `config.json` に定義されたバックテストまたは最適化タスクを実行します。<br>オプション: `-c` / `--config`（デフォルト: `config.json`）、`-t` / `--task <番号>`（0始まり）、`--offline`、`--timeout <秒>`、`-e` / `--export`（Markdown およびコンパクト CSV を出力）、`--open-report` / `--no-open-report`（ブラウザで `batch_summary.html` を自動オープン、デフォルト: `--open-report`）。 |

> **`pea5 compile` のインクルードパス（`.mqh`）に関する補足**:
> - `--include`（`-i`）を省略して `--terminal-dir` を指定した場合、`<terminal_dir>/MQL5` が存在すれば自動的に `/inc:` として MetaEditor に渡されるため、`MQL5/Include/` 配下の標準 `#include <...>` ヘッダーがそのまま利用できます。
> - `.mqh` ファイルが `<terminal_dir>/MQL5` 以外の場所にある場合は、`--include <dir>` を指定してください（例: `pea5 compile -f C:/MyEAs/MyEA.mq5 --terminal-dir C:/MT5-Portable -i C:/MyEAs/Include`）。なお、`--include` を明示指定した場合は `<terminal_dir>/MQL5` の自動 `/inc:` 設定より優先されます。

---

## 設定ファイル・認証情報リファレンス

### `config.json` スキーマ

```json
{
  "terminal": {
    "directory": "C:/MT5-Portable",
    "executable": "C:/MT5-Portable/terminal64.exe",
    "compiler": "C:/MT5-Portable/metaeditor64.exe"
  },
  "tasks": [
    {
      "name": "MA_Sample_Test",
      "expert": "C:/MT5-Portable/MQL5/Experts/Examples/Moving Average/Moving Average.ex5",
      "symbol": "EURUSD",
      "period": "H1",
      "from_date": "2026.10.01",
      "to_date": "2026.10.15",
      "deposit": 10000,
      "currency": "USD",
      "leverage": 100
    }
  ]
}
```

- `terminal`: `directory`、`executable`、`compiler` を指定します。
- `tasks`: バックテストタスクの配列です。任意項目として `set_file`、`model`、`optimization`、`optimization_criterion`、`execution_mode`、`offline`、`timeout`、`report_name`、`shutdown_terminal` などを指定できます。共通設定はトップレベルの `"common": { ... }` にまとめることも可能です。
- `tasks[].expert`: 絶対パス、`terminal.directory` からの相対パス（例: `MQL5/Experts/Examples/Moving Average/Moving Average.ex5`）、または `.mq5` パス（`.ex5` が無い場合は自動コンパイル）に対応しています。

#### マルチタスク・バッチ実行例

`"common"` に共通のデフォルト設定を記述し、`"tasks"` の各要素で**任意の設定**を上書きできます。1 回のバッチ実行で、複数の EA（`expert`）、通貨ペア（`symbol`）、時間足（`period`）、検証期間（`from_date` / `to_date`）、プリセットファイル（`set_file`）、およびバックテスト／最適化モード（`optimization`）を混在させて実行可能です：

```json
{
  "terminal": {
    "directory": "C:/MT5-Portable",
    "executable": "C:/MT5-Portable/terminal64.exe",
    "compiler": "C:/MT5-Portable/metaeditor64.exe"
  },
  "common": {
    "from_date": "2026.10.01",
    "to_date": "2026.10.15",
    "deposit": 10000,
    "currency": "USD",
    "leverage": 100
  },
  "tasks": [
    {
      "name": "MA_EURUSD_Backtest",
      "expert": "C:/MT5-Portable/MQL5/Experts/Examples/Moving Average/Moving Average.ex5",
      "symbol": "EURUSD",
      "period": "H1",
      "optimization": 0,
      "set_file": "C:/path/to/presets/conservative.set"
    },
    {
      "name": "MACD_GBPUSD_Opt",
      "expert": "C:/MT5-Portable/MQL5/Experts/Examples/MACD/MACD Sample.ex5",
      "symbol": "GBPUSD",
      "period": "H4",
      "from_date": "2026.01.01",
      "to_date": "2026.10.01",
      "optimization": 2,
      "optimization_criterion": 0,
      "set_file": "C:/path/to/presets/aggressive_opt.set"
    }
  ]
}
```

- **`"common"` と `"tasks"` のマージ仕様**: `"tasks"` の各要素は、`"common"` の設定をベースとして読み込み、タスク個別のキーで上書きして実行されます。
- **`set_file` の自動同期**: 指定された `.set` ファイルはテスト開始前に `<terminal_dir>/MQL5/Profiles/Tester/` へ自動的にコピーされ、そのファイル名が MT5 ストラテジーテスター（`ExpertParameters` / `Parameters`）に渡されます。
- **全タスク実行と個別実行**:
  - `pea5 run --config config.json` を実行すると、すべてのタスクが順番に実行されます（`report_name` を省略した場合、レポート名には `_t1`、`_t2` などが自動付与されます）。
  - `pea5 run --config config.json --task 0`（または `--task 1`）を指定すると、該当する 0 始まりのインデックスのタスクのみを実行できます。

#### 最適化テスト（`optimization`）

`pea5` は `config.json` のタスク設定（または `"common"`）を通じて、MT5 ストラテジーテスターのパラメーター最適化にも対応しています：

- `optimization`（デフォルト: `0`）: `0` = 単一バックテスト（最適化なし）、`1` = 低速な完全アルゴリズム（全探索）、`2` = 高速な遺伝的アルゴリズム。
- `optimization_criterion`（デフォルト: `0`）: `optimization > 0` のときに MT5 へ渡される最適化の評価基準（例: `0` = 残高最大、`1` = プロフィットファクター最大、`2` = 期待利得最大、`6` = カスタム最大）。
- `model`（デフォルト: `0`）: ティック生成モデル（`0` = 全ティック、`1` = 1分足 OHLC、`2` = 始値のみ、`3` = 数学的計算、`4` = リアルティックに基づく全ティック）。

> **補足**: 各パラメーターの最適化範囲（**Start / Step / Stop**）は `set_file` で指定する `.set` ファイル側で定義し、`config.json` 側で最適化モードおよび評価基準を有効化します。

```json
{
  "name": "MA_Genetic_Optimization",
  "expert": "C:/MT5-Portable/MQL5/Experts/Examples/Moving Average/Moving Average.ex5",
  "symbol": "EURUSD",
  "period": "H1",
  "from_date": "2026.01.01",
  "to_date": "2026.10.01",
  "model": 1,
  "optimization": 2,
  "optimization_criterion": 0,
  "set_file": "C:/path/to/presets/ma_opt_ranges.set"
}
```

### `credentials.json` スキーマと解決優先順位

```json
{
  "login": 12345678,
  "password": "your_password",
  "server": "Broker-DemoServer"
}
```

認証情報は以下の厳格な優先順位で解決されます：

1. `config.json` 内の `credentials` オブジェクト、`config.json` 内の `credentials_file` パス、または `config.json` と同じディレクトリの `./credentials.json`。
2. `<terminal_dir>/Config/common.ini` からの自動検出（`Login` および `Server`）。
3. ユーザーホーム設定: `~/.config/portable-ea5-tester/credentials.json`（フォールバック: `~/.config/portable-strategy-tester/credentials.json`）。
4. 環境変数: `PEA5_LOGIN`、`PEA5_PASSWORD`、`PEA5_SERVER`（フォールバック: `PST_LOGIN`、`PST_PASSWORD`、`PST_SERVER`）。

> **補足**: `--offline` モードであっても、MT5 ストラテジーテスターが `bases/<ServerName>/` 内のヒストリカルデータやシンボル仕様を参照するために `login` と `server` は必須です（オフラインテスト時は `password` を省略または空にできます）。

---

## よくある質問（FAQ）

### Q1: `/portable` を付けずに MT5 を起動してしまい、`%APPDATA%\MetaQuotes\Terminal\<32文字のハッシュ>\` が作成されました。どうすればよいですか？

**初回セットアップが完了した後であっても**、`/portable` フラグを付けずに `terminal64.exe`（または `metaeditor64.exe`）を直接ダブルクリックして起動すると、MT5 は通常モードで起動し、`C:\MT5-Portable` ではなく `%APPDATA%\MetaQuotes\Terminal\<32文字のハッシュ>\` 配下に別のデータフォルダを作成・参照します。

安全に確認・削除する手順は以下のとおりです：
1. MT5 を完全に終了します。
2. `%APPDATA%\MetaQuotes\Terminal\<32文字のハッシュ>\origin.txt` をテキストエディタで開き、ポータブルフォルダ（例: `C:\MT5-Portable`）が記載されていることを確認します。
3. 確認できたら、MT5 を閉じた状態でその `<32文字のハッシュ>` フォルダごと削除して問題ありません（`C:\MT5-Portable` 内のポータブルデータには影響しません）。
4. 今後は手動起動時に必ず `/portable` を付けたショートカットから起動するか、`pea5 login` / `pea5 run` を使用してください。

**`/portable` ショートカットの作成手順:**

- **エクスプローラー（GUI）**:
  1. `C:\MT5-Portable\terminal64.exe` を右クリックし、**ショートカットの作成** を選択します（作成したショートカットは `C:\MT5-Portable` 内に置くか、デスクトップへ移動してください）。
  2. 作成したショートカットを右クリックし、**プロパティ** を開きます。
  3. **リンク先** の末尾に ` /portable` を追記し（例: `"C:\MT5-Portable\terminal64.exe" /portable`）、**OK** をクリックします。
  4. *(任意)* `metaeditor64.exe` を手動で開く場合も同様にショートカットを作成できます。
- **PowerShell**:
  ```powershell
  $ws = New-Object -ComObject WScript.Shell
  $sc = $ws.CreateShortcut("C:\MT5-Portable\MT5-Portable.lnk")
  $sc.TargetPath = "C:\MT5-Portable\terminal64.exe"
  $sc.Arguments = "/portable"
  $sc.WorkingDirectory = "C:\MT5-Portable"
  $sc.Save()
  ```
- **コマンドプロンプト（`cmd`）**:
  ```cmd
  powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut('C:\MT5-Portable\MT5-Portable.lnk'); $sc.TargetPath = 'C:\MT5-Portable\terminal64.exe'; $sc.Arguments = '/portable'; $sc.WorkingDirectory = 'C:\MT5-Portable'; $sc.Save()"
  ```

### Q2: `pea5 compile` が失敗します（`.mqh` 不足や MQL5 構文・API エラー）。どう調査すればよいですか？

- **`.mqh` インクルード解決**: `--terminal-dir` を指定して `--include`（`-i`）を省略した場合、`pea5 compile` は `<terminal_dir>/MQL5` の存在を自動検出し、MetaEditor の `/inc:` に渡します。独自の `.mqh` ファイルを `<terminal_dir>/MQL5` の外に配置している場合は、`--include`（`-i`）で明示的に指定してください（例: `pea5 compile --file "C:/MyEAs/MyStrategy.mq5" --terminal-dir C:/MT5-Portable --include C:/MyEAs/Include`）。
- **詳細なエラー確認**: MetaEditor をポータブルモードで起動します：
  ```powershell
  C:\MT5-Portable\metaeditor64.exe /portable
  ```
  MetaEditor GUI 上で該当の `.mq5` ファイルを開いてコンパイルすると、**ツールボックス**（Toolbox）タブでエラーの詳細と正確な行番号を確認できます。

### Q3: `config.json` に Windows のパスを書くと JSON パースエラーになります。

Windows のパスを JSON 内に書く際、単一のバックスラッシュ `\` はエスケープ文字として解釈されるため JSON パースエラーになります。スラッシュ `/`（推奨、例: `"C:/MT5-Portable"`）または二重バックスラッシュ `\\`（例: `"C:\\MT5-Portable"`）を使用してください。

### Q4: `pip install` せずに実行する方法はありますか？また、新しいターミナルで `pea5` が見つからないのはなぜですか？

- **一時的な実行（`PYTHONPATH`）**: PowerShell で `$env:PYTHONPATH = "."`（または `cmd` で `set PYTHONPATH=.`）を設定するとインストールなしで `python -m portable_ea5_tester <サブコマンド>` を実行できますが、この設定は **現在開いているターミナルセッション限りの一時的なもの** であり、ターミナルを閉じるとリセットされます。
- **継続的な利用（`pip install`）**: 継続して利用する場合は、Step 2 の方法 A に従って `.venv` を作成・有効化し、`pip install .` を実行してください（`.venv` 有効化中に `pea5` コマンドが利用できます）。

### Q5: 複数の EA、通貨ペア、`.set` プリセット、バックテスト／最適化を一度にまとめて実行できますか？

はい。共通のデフォルト設定を `"common"` に記述し、`"tasks"` 配列の各要素で `expert`、`symbol`、`period`、`from_date` / `to_date`、`set_file`、`optimization` など**任意の設定**を上書きして実行できます（上記の「[マルチタスク・バッチ実行例](#マルチタスクバッチ実行例)」を参照）。
- すべてのタスクを順番に実行: `pea5 run --config config.json`
- 0 始まりのインデックスで特定タスクのみ実行: `pea5 run --config config.json --task 0`（または `--task 1`）

---

## サポートおよびバグ報告

- 本プロジェクトは **AS-IS（現状有姿）** で提供されており、個別のカスタマーサポートや保証された SLA は提供していません。
- バグ報告、お問い合わせ、フィードバックはベストエフォート（返答や SLA の保証なし）にて `hjquantlab@gmail.com` までお送りください。
- 今後の開発ロードマップの優先順位や Pro 版に関する決定は、ユーザーからのフィードバック、GitHub のスター数、およびコミュニティの反響に直接基づいて行われます。

---

## ライセンス

本プロジェクトは [MIT License](LICENSE) のもとで公開されています。  
Copyright (c) 2026 hjQuantLab — [https://github.com/hjquantlab/portable-ea5-tester](https://github.com/hjquantlab/portable-ea5-tester)
