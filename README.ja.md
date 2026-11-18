# Portable Strategy Tester (`portable-ea5-tester`)

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[English](README.md) | [日本語](README.ja.md)

**Portable Strategy Tester**（`pea5`）は、MetaTrader 5 の Expert Advisor（`.mq5` → `.ex5`）のコンパイルおよび Strategy Tester によるバックテスト・パラメータ最適化を自動化する、軽量・スタンドアロンな CLI フレームワークです。

> **重要**: `portable-ea5-tester` は **`/portable` モードで動作する MetaTrader 5 のみに対応** しています。ユーザーデータを `%APPDATA%` に分割保存する通常の MT5 インストール構成には対応していません。

## 目次

1. [主な特徴](#1-主な特徴)
2. [動作要件](#2-動作要件)
3. [クイックスタート (3ステップ)](#3-クイックスタート-3ステップ)
4. [仕組み](#4-仕組み)
   - [4.1 `config.json` と `.set` ファイルの役割](#41-configjson-と-set-ファイルの役割)
   - [4.2 EA の解決とコンパイル](#42-ea-の解決とコンパイル)
   - [4.3 `.set` ファイルの解決](#43-set-ファイルの解決)
5. [バックテストと最適化のパターン](#5-バックテストと最適化のパターン)
6. [出力レポート](#6-出力レポート)
7. [リファレンス](#7-リファレンス)
   - [7.1 CLI サブコマンド](#71-cli-サブコマンド)
   - [7.2 `config.json` パラメータ](#72-configjson-パラメータ)
   - [7.3 レポート命名オプション](#73-レポート命名オプション)
   - [7.4 認証情報](#74-認証情報)
8. [トラブルシューティングと FAQ](#8-トラブルシューティングと-faq)
9. [保守とサポートポリシー](#9-保守とサポートポリシー)
10. [ライセンス](#10-ライセンス)

## 1. 主な特徴

- **外部依存ゼロ**: Python 標準ライブラリのみで構成されています（`dependencies = []`）。
- **ヘッドレス MT5 自動化**: 単一の `config.json` から、EA コンパイル（`metaeditor64.exe`）、シングルバックテスト、パラメータ最適化、マルチタスク一括実行（`terminal64.exe /portable`）を実行できます。
- **AI・分析フレンドリーな出力**: HTML / JSON レポートおよび `batch_summary.html` / `batch_summary.json` を自動生成し、`--export` 指定時には Markdown（`*_report.md`）や CSV（`*_trades.csv`）も出力します。

## 2. 動作要件

- **OS**: Windows 10 / 11（64-bit 必須）。MetaTrader 5 ポータブルモード（`terminal64.exe` / `metaeditor64.exe`）および本ツールは、ネイティブ Windows 環境専用としてテスト・提供されています。macOS および Linux はネイティブ非対応です。なお、Linux/macOS の Wine/Proton 環境下でポータブル MT5 が起動する可能性はありますが、動作確認は行っておらず対象外（Untested & Out of scope）となります。
- **Python**: Python 3.9 以上
- **MetaTrader 5**: `terminal64.exe` および `metaeditor64.exe` を含むポータブル版 MT5 ディレクトリ

---

## 3. クイックスタート (3ステップ)

### Step 1: ポータブル MT5 の準備

1. MetaQuotes またはご利用のブローカーから MetaTrader 5 をインストールします（未インストールの場合）。
2. 専用フォルダ（例: `C:\MT5-Portable`）を作成し、通常インストール先（例: `C:\Program Files\MetaTrader 5`）から `terminal64.exe` と `metaeditor64.exe` を `C:\MT5-Portable` にコピーします。
3. `/portable` フラグ付きで MT5 を **1回だけ** 起動して `C:\MT5-Portable` 内に `MQL5/` と `Config/` を初期化し、起動後に MT5 を閉じます:
   ```powershell
   C:\MT5-Portable\terminal64.exe /portable
   ```

> **注意**: MetaEditor を手動または直接起動する場合も、データを `%APPDATA%` ではなくポータブルディレクトリ内に保持するため、同様に `/portable`（`C:\MT5-Portable\metaeditor64.exe /portable`）が必要です。
> `/portable` ショートカットの作成方法や、誤って通常モードで起動した場合のクリーンアップ手順は [FAQ Q1](#8-トラブルシューティングと-faq) を参照してください。

### Step 2: pea5 のインストール

リポジトリをクローンし、仮想環境内に `pea5` をインストールします（標準的な一例・推奨）:

- **PowerShell**:
  ```powershell
  git clone https://github.com/hjquantlab/portable-ea5-tester.git
  cd portable-ea5-tester
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install .
  ```
- **コマンドプロンプト (`cmd.exe`)**:
  ```cmd
  git clone https://github.com/hjquantlab/portable-ea5-tester.git
  cd portable-ea5-tester
  python -m venv .venv
  .venv\Scripts\activate.bat
  pip install .
  ```

#### お試し実行 / 直接実行（インストール不要）

Python 環境へインストールせず、リポジトリのルートから直接動作確認を行う場合:

- **Windows（PowerShell / コマンドプロンプト）**:
  ```powershell
  python -m portable_ea5_tester --help
  ```

> **注記**: この直接実行方式は環境へのインストールを行わないため、ターミナルを閉じると終了し、システムや仮想環境の PATH に `pea5` コマンドが残ることもありません（リポジトリのルートフォルダでのみ動作します）。手軽な動作確認用を想定しているため、定常的に利用する場合は上記の一例のように仮想環境へのインストールを推奨します。

<details>
<summary>その他のインストール方法（uv / グローバル pip / Editable 等の一例）</summary>

`uv` や `conda` など他の環境管理ツールをお使いの場合は、適宜読み替えて実行してください:

- **`uv` を使用する場合**:
  ```powershell
  uv venv .venv
  .\.venv\Scripts\Activate.ps1
  uv pip install .
  ```
- **グローバル `pip` インストール**（仮想環境なし）:
  ```powershell
  pip install .
  # システムパッケージマネージャ管理環境の場合:
  pip install --break-system-packages .
  ```
- **Editable インストール**:
  ```powershell
  pip install -e .
  ```

</details>

### Step 3: 設定とスモークテストの実行

サンプルファイルをコピーして、ローカル用の設定ファイルと認証情報ファイルを作成します:

```powershell
copy config.example.json config.json
copy credentials.example.json credentials.json
```

> **JSON パス記法の注意**: JSON ファイル内のパスにはスラッシュ `/`（例: `"C:/MT5-Portable"`）またはエスケープされたバックスラッシュ `\\` を使用してください。単一の `\` は JSON 構文エラーになります。

`credentials.json` にブローカー口座の `login`・`password`・`server` を記入し、以下の 4 コマンドで動作確認を行います（その他の認証情報の指定方法は [7.4 認証情報](#74-認証情報) を参照）:

```powershell
# 1. MT5 端末・コンパイラ・認証情報のパスを診断
pea5 init --config config.json

# 2. MT5 GUI を1回起動してログイン情報をキャッシュし履歴データを同期（ログイン後に MT5 を閉じる）
pea5 login --config config.json

# 3. MQL5 EA（.mq5 -> .ex5）をコンパイル
pea5 compile --file "C:/MT5-Portable/MQL5/Experts/Examples/Moving Average/Moving Average.mq5" --terminal-dir "C:/MT5-Portable"

# 4. サンプルバックテストを実行し、Markdown / CSV サマリーをエクスポート
pea5 run --config config.json --export
```

---

## 4. 仕組み

### 4.1 `config.json` と `.set` ファイルの役割

- **`config.json`** は「*何を・どの環境で* 実行するか」を制御します（端末パス、EA（`expert`）、通貨ペア、時間足（`period`）、検証期間（`from_date` / `to_date`）、口座設定（`deposit`・`currency`・`leverage`）、実行/最適化モード（`model`・`optimization`・`optimization_criterion`）、レポート出力設定）。
- **`.set` ファイル**（任意）は「*EA 内部の入力パラメータ*（`.mq5` 内の `input` 変数）」を制御します。シングルバックテスト用の固定値上書き、または最適化用の Start / Step / Stop 範囲を指定します。

### 4.2 EA の解決とコンパイル

`pea5 run` が EA をコンパイルするかどうかは、`expert` の拡張子で決まります:

| `expert` の値 | 動作 |
| :--- | :--- |
| `.mq5`（例: `EA.mq5`） | `.ex5` が既に存在していても、テスト前に **必ずコンパイル** します。同じ `.mq5` は 1 回の `pea5 run` で 1 回だけコンパイルされます（後続タスクは再利用）。 |
| `.ex5`（例: `EA.ex5`） | そのまま使用します。**コンパイルしません。** |
| 拡張子なし（例: `EA`） | `EA.ex5` があればそれを使用します。`.ex5` がない場合のみ `EA.mq5` をコンパイルします。 |

- **コンパイル出力先**: `.ex5` は **ソース `.mq5` と同じフォルダ**（同じベース名）に出力されます。既存の `.ex5` は上書きされます。
- **配置**: 解決された `.ex5` は `<terminal_dir>/MQL5/Experts/` に自動コピーされます。手動コピーは不要です。
- **探索順序**: 指定パスそのまま → `<terminal_dir>/<パス>` → `<terminal_dir>/MQL5/Experts/<ファイル名>`。
- コンパイルエラー、または `.ex5` が更新されなかった場合、タスクはエラーで停止します。

### 4.3 `.set` ファイルの解決

- `set_file` は **任意** です。省略すると EA のデフォルト入力値で実行されます。
- 相対パスはカレントディレクトリ基準で解決し、絶対パスはそのまま使用します。`.set` 拡張子は省略可能です。
- **探索順序**: 指定パスそのまま → `<terminal_dir>/<パス>` → `<terminal_dir>/MQL5/Profiles/Tester/<ファイル名>`。
- 見つかったファイルは `<terminal_dir>/MQL5/Profiles/Tester/` に自動コピーされます。

---

## 5. バックテストと最適化のパターン

### パターン選択表

| パターン | 用途 | `optimization` | `set_file` | 設定構造 |
| :--- | :--- | :---: | :---: | :--- |
| **1. シングルバックテスト（初期値）** | EA のデフォルトパラメータでの基準テスト | `0` | 省略 | 単一タスク |
| **2. シングルバックテスト（カスタム値）** | 特定の固定 EA パラメータでの検証 | `0` | 固定 `Key=Value` 形式 `.set` | 単一タスク |
| **3. パラメータ最適化** | 1 つまたは複数パラメータの総当たり/遺伝的探索 | `1` または `2` | 範囲 `Key=Val\|\|Start\|\|Step\|\|Stop\|\|Y` `.set` | 単一タスク |
| **4. マルチタスク一括実行** | タスクごとに通貨ペア・時間足・期間・モード・EA・`.set`・口座条件を変更 | タスクごとに `0`/`1`/`2` | タスクごとに任意 | `common` + `tasks[]` |

### パターン 1: シングルバックテスト（EA デフォルトパラメータ）

`set_file` を省略すると、EA にコンパイル済みのデフォルト入力値で実行されます。`expert` に `.mq5` を指定しているため、テスト前にコンパイルされます（[4.2 EA の解決とコンパイル](#42-ea-の解決とコンパイル) を参照）。

```json
{
  "terminal": {
    "directory": "C:/MT5-Portable"
  },
  "tasks": [
    {
      "expert": "C:/MT5-Portable/MQL5/Experts/Examples/Moving Average/Moving Average.mq5",
      "symbol": "EURUSD",
      "period": "H1",
      "from_date": "2026.01.01",
      "to_date": "2026.06.01",
      "deposit": 10000,
      "currency": "USD",
      "leverage": 100
    }
  ]
}
```

> 全タスクキー: [7.2 `config.json` パラメータ](#72-configjson-パラメータ) を参照。

### パターン 2: カスタムパラメータでのシングルバックテスト

`Key=Value` 形式で 1 つ以上の EA 入力パラメータを上書きする標準 MT5 `.set` ファイルを `set_file` に指定します:

```ini
; presets/ma_custom.set
MaximumRisk=0.05
DecreaseFactor=3
MovingPeriod=24
MovingShift=2
```

> **ヒント**: 正確なパラメータ名を含む `.set` ファイルは、MT5 Strategy Tester の「**パラメーター**（Inputs）」タブ上で右クリック →「**保存**」から直接書き出すこともできます。

```json
{
  "terminal": {
    "directory": "C:/MT5-Portable"
  },
  "tasks": [
    {
      "expert": "C:/MT5-Portable/MQL5/Experts/Examples/Moving Average/Moving Average.ex5",
      "set_file": "presets/ma_custom.set",
      "symbol": "EURUSD",
      "period": "H1",
      "from_date": "2026.01.01",
      "to_date": "2026.06.01"
    }
  ]
}
```

> 全タスクキー: [7.2 `config.json` パラメータ](#72-configjson-パラメータ) を参照。

### パターン 3: パラメータ最適化（単一パラメータ・複数パラメータ同時探索）

MT5 の最適化用 `.set` ファイルは、`||` で区切られた 5 フィールド構文を使用します:

```ini
ParameterName=Value||Start||Step||Stop||Y/N
```

- **`||N`**: パラメータを `Value` に固定します（最適化対象外）。
- **`||Y`**: `Start` から `Stop` まで `Step` 刻みで探索します。
  - **単一パラメータ最適化**: 最適化したい **1 つのパラメータのみ `||Y`** とし、他を `||N` にします。
  - **複数パラメータ同時最適化**: **2 つ以上のパラメータを `||Y`** にします。有効化された全パラメータの組み合わせが評価されます（下記例では `5 × 5 × 11 = 275` 通り）:

```ini
; presets/ma_optimize.set
MaximumRisk=0.02||0.01||0.01||0.05||Y
DecreaseFactor=3||1||1||5||Y
MovingPeriod=12||10||2||30||Y
MovingShift=0||0||1||10||N
```

`config.json` で `optimization` を設定します:
- `1`: **完全なアルゴリズム（低速）** — すべての組み合わせを網羅的に評価します。
- `2`: **遺伝的アルゴリズム（高速）** — 組み合わせ数が多い複数パラメータ最適化に推奨されます。

`optimization_criterion`（`0`–`6`）で評価基準を指定できます:
- `0`: 最大残高 | `1`: 最大プロフィットファクター | `2`: 最大期待利得 | `3`: 最小ドローダウン | `4`: 最大リカバリーファクター | `5`: 最大シャープレシオ | `6`: カスタム最大値（`OnTester()`）

```json
{
  "terminal": {
    "directory": "C:/MT5-Portable"
  },
  "tasks": [
    {
      "expert": "C:/MT5-Portable/MQL5/Experts/Examples/Moving Average/Moving Average.ex5",
      "set_file": "presets/ma_optimize.set",
      "symbol": "EURUSD",
      "period": "H1",
      "from_date": "2025.01.01",
      "to_date": "2025.12.31",
      "optimization": 2,
      "optimization_criterion": 5
    }
  ]
}
```

> 全タスクキー: [7.2 `config.json` パラメータ](#72-configjson-パラメータ) を参照。

### パターン 4: マルチタスク一括実行（`common` + `tasks`）

`tasks[]` は `.set` ファイルの切り替えだけに限定されません。共通設定を `common` に記述し、**`tasks[]` の各タスクで任意のテスト条件を個別に変更**できます（時間足 `period`、検証期間 `from_date` / `to_date`、実行モード `optimization` / `optimization_criterion` / `model`、通貨ペア `symbol`、EA `expert`、`set_file`、口座設定 `deposit` / `leverage`）。

```json
{
  "terminal": {
    "directory": "C:/MT5-Portable"
  },
  "common": {
    "currency": "USD",
    "deposit": 10000,
    "leverage": 100,
    "model": 0,
    "report_dir": "reports/batch_study"
  },
  "tasks": [
    {
      "name": "EURUSD_M15_InSample_Opt",
      "expert": "C:/MT5-Portable/MQL5/Experts/Examples/Moving Average/Moving Average.ex5",
      "set_file": "presets/ma_optimize.set",
      "symbol": "EURUSD",
      "period": "M15",
      "from_date": "2025.01.01",
      "to_date": "2025.12.31",
      "optimization": 2,
      "optimization_criterion": 4
    },
    {
      "name": "EURUSD_H1_OutOfSample_Verify",
      "expert": "C:/MT5-Portable/MQL5/Experts/Examples/Moving Average/Moving Average.ex5",
      "set_file": "presets/ma_custom.set",
      "symbol": "EURUSD",
      "period": "H1",
      "from_date": "2026.01.01",
      "to_date": "2026.06.01",
      "optimization": 0
    },
    {
      "name": "GBPUSD_H4_MACD_HighLev",
      "expert": "C:/MT5-Portable/MQL5/Experts/Examples/MACD/MACD Sample.ex5",
      "symbol": "GBPUSD",
      "period": "H4",
      "from_date": "2026.01.01",
      "to_date": "2026.06.01",
      "optimization": 0,
      "deposit": 50000,
      "leverage": 200
    }
  ]
}
```

全タスクを順番に実行するか、0 始まりのインデックスで特定タスクのみ実行できます:

```powershell
# 全 3 タスクを実行
pea5 run --config config.json

# インデックス 0（最初のタスク）のみ実行
pea5 run --config config.json --task 0
```

> 全タスクキー: [7.2 `config.json` パラメータ](#72-configjson-パラメータ) を参照。

---

## 6. 出力レポート

| 実行種別 | 生成される出力物（`report_dir` 内） | 備考 |
| :--- | :--- | :--- |
| **シングルバックテスト**（`optimization: 0`） | `<ReportName>.html`, `<ReportName>.json`, `*.png` | `output_formats.keep_charts` と `output_formats.html` が `true` の場合 `*.png` チャート画像を保持します。 |
| **シングルバックテスト + `--export`** | `<ReportName>_report.md`, `<ReportName>_trades.csv`, `<ReportName>_metrics.json` を追加生成 | ノートブックや LLM 分析向けの Markdown / コンパクト CSV 形式です。 |
| **最適化**（`optimization > 0`） | `<ReportName>.xml`, `<ReportName>.html`, `<ReportName>.json` | `.html` は生成された最適化ダッシュボード、`.json` には `passes` と `best_pass` が含まれます。 |
| **バッチサマリー**（毎回の `pea5 run` 実行時） | `batch_summary.html`, `batch_summary.json` | 集計ダッシュボードおよび JSON サマリーがレポートディレクトリに出力されます。 |

> 出力フォルダ・ファイル名・プレースホルダー: [7.3 レポート命名オプション](#73-レポート命名オプション) を参照。

---

## 7. リファレンス

### 7.1 CLI サブコマンド

| コマンド | 用途 | 主なオプション |
| :--- | :--- | :--- |
| `pea5 init` | `config.json`・MT5 端末・MetaEditor・認証情報の診断 | `--config` / `-c`（デフォルト: `config.json`） |
| `pea5 login` | Login/Server を事前入力した状態で MT5 GUI（`/portable`）を起動し認証情報をキャッシュ | `--config` / `-c`（デフォルト: `config.json`） |
| `pea5 compile` | `metaeditor64.exe` による `.mq5` → `.ex5` のヘッドレスコンパイル | `--file` / `-f`（必須）, `--compiler`, `--terminal-dir`（`/inc:<terminal_dir>/MQL5` を自動付与）, `--include` / `-i`（`<terminal_dir>/MQL5` 外の外部インクルードルートを指定する任意オプション）, `--timeout`（デフォルト: `60`） |
| `pea5 run` | バックテストまたは最適化タスクを実行（.mq5 指定時は事前コンパイルも自動実行） | `--config` / `-c`（デフォルト: `config.json`）, `--task` / `-t`, `--offline`, `--timeout`, `--export` / `-e`, `--no-open-report` |

> **`pea5 compile` の出力先とインクルード設定**: `.ex5` バイナリは `--file` のソースと同じフォルダ（同じベース名）に出力されます。`--terminal-dir` を指定すると MetaEditor のインクルード探索パスに `/inc:<terminal_dir>/MQL5` が自動的に追加されます。`--include` は `<terminal_dir>/MQL5` 外にある独自の外部ヘッダーディレクトリを探索させる場合にのみ指定する任意オプションです。なお、`pea5 compile` 単体では `<terminal_dir>/MQL5/Experts/` への自動コピーは行われません（このコピーは `pea5 run` 実行時に自動で行われます）。
>
> **MetaEditor の手動実行**: `pea5` を介さずに `metaeditor64.exe` を手動起動する場合は、データを `%APPDATA%` ではなくポータブル領域内に保持するため、必ず `/portable`（例: `C:\MT5-Portable\metaeditor64.exe /portable`）を付与してください。

### 7.2 `config.json` パラメータ

#### `terminal` セクション

| キー | 説明 |
| :--- | :--- |
| `directory` | ポータブル MT5 ルートフォルダへのパス（フラット指定の `terminal_dir` も互換サポート）。 |
| `executable` | `terminal64.exe` への明示的パス（`directory` 指定時は省略可）。 |
| `compiler` | `metaeditor64.exe` への明示的パス（`directory` 指定時は省略可）。 |

#### `common` / `tasks[]` セクション

| キー | デフォルト | 説明 |
| :--- | :--- | :--- |
| `expert` | *必須* | EA のパスまたはファイル名（`.mq5`・`.ex5`・拡張子なし）。[4.2](#42-ea-の解決とコンパイル) を参照。 |
| `symbol` | *必須* | ブローカーのシンボル名（例: `"EURUSD"`）。 |
| `period` | *必須* | 時間足（`M1`, `M5`, `M15`, `M30`, `H1`, `H4`, `D1`, `W1`, `MN1`）。 |
| `from_date` | *必須* | 開始日（`YYYY.MM.DD` または `YYYY-MM-DD`）。 |
| `to_date` | *必須* | 終了日（`YYYY.MM.DD` または `YYYY-MM-DD`）。 |
| `set_file` | `null` | 任意の `.set` プリセットファイルパス。[4.3](#43-set-ファイルの解決) を参照。 |
| `model` | `0` | ティックモデル: `0`（全ティック）, `1`（1 分足 OHLC）, `2`（始値のみ）, `3`（数値計算）, `4`（リアルティックに基づく全ティック）。 |
| `optimization` | `0` | `0`（無効）, `1`（完全アルゴリズム）, `2`（遺伝的アルゴリズム）, `3`（気配値表示の全銘柄）。 |
| `optimization_criterion` | `0` | `0`–`6`（残高, PF, 期待利得, DD 最小, リカバリーファクター, シャープレシオ, カスタム `OnTester`）。 |
| `execution_mode` | `0` | 約定遅延 ms（`0` = 遅延なし, `-1` = ランダム遅延）。 |
| `deposit` | `10000` | 初期証拠金。 |
| `currency` | `"USD"` | 口座通貨。 |
| `leverage` | `50`（`config.example.json` では `100`） | レバレッジ（`1:N` の整数 `N`）。 |
| `shutdown_terminal` | `true` | テスト完了後に MT5 を自動終了するかどうか。 |
| `offline` | `false` | パスワード省略時の厳格な認証エラーをスキップします。 |
| `timeout` | `600` | タスクあたりのプロセスタイムアウト（秒）。 |
| `heartbeat_interval` | `10.0` | コンソール進捗ハートビートの間隔（秒）。 |
| `min_history_quality` | `90.0` | この割合（%）を下回った場合に履歴データ品質警告を表示します。 |
| `output_formats` | `{ "html": true, "json": true, "keep_charts": true, "batch_summary_json": true }` | 生成する HTML、JSON、チャート `.png`、`batch_summary.json` の出力有無（`common` で設定）。 |

### 7.3 レポート命名オプション

`common` または `tasks[]` 内の各タスクで以下のキーを設定できます:

| キー | デフォルト | 説明 |
| :--- | :--- | :--- |
| `report_dir` | `"reports"` | 出力先ディレクトリ（`config.json` からの相対パスまたは絶対パス）。 |
| `report_name` | 自動（`Report_<symbol>_<period>[_<set>][_opt]`） | カスタムファイル名テンプレート（拡張子は自動付与。複数タスク実行時に省略された場合は `_t1`, `_t2` を自動付加）。 |
| `use_subfolder` | `false` | `true` の場合、`report_dir` 配下にサブフォルダを作成します。 |
| `folder_template` | `"{date}_{ea}"` | `use_subfolder` が `true` のときのサブフォルダ名テンプレート。 |
| `auto_increment` | `false` | 出力先レポートファイルが既に存在する場合に `_01`, `_02`, ... を付加します。 |
| `subfolder_auto_increment` | `auto_increment` と同値 | 出力先サブフォルダが既に存在する場合に `_01`, `_02`, ... を付加します。 |

**利用可能なプレースホルダー**（`report_name` および `folder_template` で使用可能）:

| プレースホルダー | 展開値 | 例 |
| :--- | :--- | :--- |
| `{datetime}` | `YYYYMMDD_HHMMSS` | `20261116_143022` |
| `{date}` | `YYYYMMDD` | `20261116` |
| `{time}` | `HHMMSS` | `143022` |
| `{ea}` | EA ファイルベース名（サニタイズ済み） | `Moving Average` |
| `{symbol}` | 通貨ペア名 | `EURUSD` |
| `{period}` | 時間足 | `H1` |
| `{set}` | `.set` ファイルベース名、未指定時は `"default"` | `ma_custom` |
| `{type}` | `optimization > 0` なら `"opt"`、それ以外は `"test"` | `test` |

#### 設定例と出力パス

```json
{
  "common": {
    "use_subfolder": true,
    "folder_template": "{date}_{ea}",
    "report_name": "Report_{symbol}_{period}_{set}"
  }
}
```

例えば `2026-03-30` に EA `Moving Average`、通貨ペア `USDJPY`、時間足 `H1`、プリセット `set1.set` で実行した場合の出力先パスは以下のようになります:

```
reports/20260330_Moving Average/Report_USDJPY_H1_set1.html
```

### 7.4 認証情報

#### `credentials.json` スキーマ

```json
{
  "login": 12345678,
  "password": "your_password",
  "server": "Broker-DemoServer"
}
```

#### 解決優先順位

1. `config.json`（`credentials` オブジェクト、`credentials_file` パス、または `config.json` と同階層の `./credentials.json`）
2. ポータブル MT5 端末内の `<terminal_dir>/Config/common.ini`（`Login` と `Server` の自動検出）
3. ユーザーホーム設定（`~/.config/portable-ea5-tester/credentials.json`、フォールバック `~/.config/portable-strategy-tester/credentials.json`）
4. 環境変数（`PEA5_LOGIN`, `PEA5_PASSWORD`, `PEA5_SERVER`、フォールバック `PST_LOGIN`, `PST_PASSWORD`, `PST_SERVER`）

> **`--offline` に関する注意**: オフラインモードであっても、MT5 が `bases/<ServerName>/` 配下のヒストリカルデータやシンボル仕様を参照するため、`login` と `server` は **引き続き必須** です。事前に `pea5 login` で認証情報をキャッシュ済みであれば `password` のみ省略可能です。

---

## 8. トラブルシューティングと FAQ

<details>
<summary>Q1: /portable なしで terminal64.exe を起動してしまった、または安全なショートカットを作りたい</summary>

1. **`/portable` ショートカットの作成**:
   - ポータブル MT5 フォルダ内の `terminal64.exe`（例: `C:\MT5-Portable\terminal64.exe`）を右クリック →「**ショートカットの作成**」。
   - 作成したショートカットを右クリック →「**プロパティ**」→「**リンク先**」の末尾に ` /portable` を追記します（例: `"C:\MT5-Portable\terminal64.exe" /portable`）。
2. **誤って通常起動したフォルダの安全なクリーンアップ（`origin.txt` の仕組み）**:
   - MT5 を通常モード（非ポータブル）で起動すると、`%APPDATA%\MetaQuotes\Terminal\<hash>\` 配下に 32 文字の 16 進数ハッシュフォルダが作成されます。その中の `origin.txt` には、そのハッシュフォルダを生成した MT5 の正確なインストール先ディレクトリ（例: `D:\Trading\MT5_Main` や `C:\Program Files\MetaTrader 5` 等）が記録されています（`C:\MT5-Portable` は本ドキュメントにおける一例です）。
   - **安全なクリーンアップ手順**:
     1. すべての MT5 を終了させた状態で、エクスプローラーで `%APPDATA%\MetaQuotes\Terminal\` を開きます。
     2. 各 32 文字のハッシュフォルダ内にある `origin.txt` を開き、どのディレクトリから生成されたかを確認します。
     3. その `origin.txt` が誤って `/portable` なしで起動してしまったポータブル MT5 のパスを指しているフォルダのみを削除します。
     4. 通常インストールして運用している常用 MT5 端末のパスが記載されたフォルダは **絶対に削除しないでください**。

</details>

<details>
<summary>Q2: pea5 compile でインクルードファイル（.mqh）が見つからない、または MetaEditor が GUI で開く</summary>

- **`.mqh` ヘッダーが見つからない場合**: `--terminal-dir` を指定すると、`pea5` は自動的に `/inc:<terminal_dir>/MQL5` を MetaEditor のインクルード探索パスに追加します。`--include` は `<terminal_dir>/MQL5` 外にある独自の外部ヘッダーディレクトリを探索させる場合にのみ指定する任意オプションです:
  1. **標準コンパイル**（端末標準ライブラリを使用。MetaEditor は自動で `C:/MT5-Portable/MQL5` をインクルードします）:
     ```powershell
     pea5 compile --file Experts/MyEA.mq5 --terminal-dir "C:/MT5-Portable"
     ```
  2. **外部インクルードルートを指定するカスタムコンパイル**:
     ```powershell
     pea5 compile --file Experts/MyEA.mq5 --terminal-dir "C:/MT5-Portable" --include "C:/SharedMQL5"
     ```
- **MetaEditor が GUI で開く / `%APPDATA%` を参照する場合**: 必ず `metaeditor64.exe` がポータブル MT5 フォルダ内に配置されていることを確認してください。また、MetaEditor を手動起動したりショートカットを作成する際も必ず `/portable`（例: `C:\MT5-Portable\metaeditor64.exe /portable`）を付与してください。付与しない場合、ポータブル領域ではなく通常版の `%APPDATA%` を参照してしまいます。

</details>

<details>
<summary>Q3: バックテストが 0 トレードで終了する / [AGENT SYNC ERROR] / [MISSING HISTORY DATA] / [INVALID SYMBOL ERROR]</summary>

- **`[AGENT SYNC ERROR]` / `[ACCOUNT SETUP REQUIRED]`**: `pea5 login --config config.json` を実行し、パスワードを入力して「**パスワードを保存**」にチェックを入れ、OK を押した後に MT5 を閉じてください。
- **`[MISSING HISTORY DATA]` / `min_history_quality` 低下**: `C:\MT5-Portable\terminal64.exe /portable` で対象通貨ペア・時間足のチャートを開き（または Strategy Tester / ヒストリーセンターで過去へスクロールし）、対象期間の M1 ヒストリカルデータをダウンロードしてください。
- **`[INVALID SYMBOL ERROR]`**: MT5 の「気配値表示（Market Watch）」でブローカー固有のシンボル名サフィックス（例: `EURUSD.m`, `EURUSDpro`, `EURUSD#`）を確認し、`config.json` に一致させてください。
- **履歴が正常でも 0 トレードになる場合**: EA ロジック、スプレッド/ロット制約、および `.set` パラメータ範囲を確認してください。

</details>

---

## 9. 保守とサポートポリシー

- **現状有姿での提供**: 本ツールは MIT ライセンスに基づき、いかなる保証や個別サポート義務も伴わない **現状有姿（As-Is）** で提供されます。
- **プロジェクトの範囲と制限**: 本ツールは主として内部の研究・自動化ワークフローのために保守されています。個別の環境トラブルシューティング、個別要望による機能開発、および非対応環境（Wine/macOS 等）への対応はプロジェクトの対象外となります。
- **連絡先**: 脆弱性の報告や重要なお問い合わせは `hjquantlab@gmail.com` までご連絡ください。

## 10. ライセンス

MIT License — Copyright (c) 2026 hjQuantLab. 詳細は [LICENSE](LICENSE) を参照してください。
