# Portable Strategy Tester (`portable-ea5-tester`)

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[English](README.md) | [日本語](README.ja.md)

**Portable Strategy Tester** (`pea5`) is a lightweight, standalone CLI framework for compiling MetaTrader 5 Expert Advisors (`.mq5` to `.ex5`) and automating Strategy Tester backtests and parameter optimizations.

> **Important**: `portable-ea5-tester` **only supports MetaTrader 5 running in `/portable` mode**. Standard MT5 installations that split user data into `%APPDATA%` are not supported.

## Table of Contents

1. [Key Features](#1-key-features)
2. [Prerequisites](#2-prerequisites)
3. [Quick Start (3 Steps)](#3-quick-start-3-steps)
4. [How It Works](#4-how-it-works)
   - [4.1 `config.json` vs `.set` Files](#41-configjson-vs-set-files)
   - [4.2 EA Resolution & Compilation](#42-ea-resolution--compilation)
   - [4.3 `.set` File Resolution](#43-set-file-resolution)
5. [Backtest & Optimization Patterns](#5-backtest--optimization-patterns)
6. [Output Reports](#6-output-reports)
7. [Reference](#7-reference)
   - [7.1 CLI Subcommands](#71-cli-subcommands)
   - [7.2 `config.json` Parameters](#72-configjson-parameters)
   - [7.3 Report Naming Options](#73-report-naming-options)
   - [7.4 Credentials](#74-credentials)
8. [Troubleshooting & FAQ](#8-troubleshooting--faq)
9. [Maintenance & Support Policy](#9-maintenance--support-policy)
10. [License](#10-license)

## 1. Key Features

- **Zero External Dependencies**: Built strictly on the Python standard library (`dependencies = []`).
- **Headless MT5 Automation**: Compile EAs (`metaeditor64.exe`) and run single backtests, parameter optimizations, and multi-task batches (`terminal64.exe /portable`) from a single `config.json`.
- **AI- & Analyst-Ready Outputs**: Automatically generates HTML/JSON reports, `batch_summary.html` / `batch_summary.json`, and optional `--export` Markdown (`*_report.md`) and CSV (`*_trades.csv`) artifacts.

## 2. Prerequisites

- **OS**: Windows 10 / 11 (64-bit required). MetaTrader 5 portable mode (`terminal64.exe` / `metaeditor64.exe`) and this tool are supported and tested exclusively on native Windows. macOS and Linux are not natively supported; while portable MT5 may run under Wine/Proton, such compatibility is untested and out of scope.
- **Python**: Python 3.9 or higher
- **MetaTrader 5**: A portable MT5 directory containing `terminal64.exe` and `metaeditor64.exe`

---

## 3. Quick Start (3 Steps)

### Step 1: Prepare Portable MT5

1. Install MetaTrader 5 (from MetaQuotes or your broker) if not already installed.
2. Create a dedicated folder (e.g., `C:\MT5-Portable`) and copy `terminal64.exe` and `metaeditor64.exe` from your installation folder (e.g., `C:\Program Files\MetaTrader 5`) into `C:\MT5-Portable`.
3. Launch MT5 **once** with the `/portable` flag so it initializes `MQL5/` and `Config/` inside `C:\MT5-Portable`, then close MT5.
   Using the built-in launcher setup tool is recommended—first generate `launch_mt5_portable.bat` inside your portable MT5 folder:
   ```powershell
   python -m portable_ea5_tester setup "C:\MT5-Portable"
   # Or, once pea5 is installed:
   pea5 setup "C:\MT5-Portable"
   ```
   Then double-click or run `launch_mt5_portable.bat` inside `C:\MT5-Portable` to verify the exact `terminal64.exe` path and safely launch it with `/portable` after confirming the `y/n` prompt.
   (Or run directly: `C:\MT5-Portable\terminal64.exe /portable`)

> **Note**: If MetaEditor is launched manually or directly, it also requires `/portable` (`C:\MT5-Portable\metaeditor64.exe /portable`) to keep data inside the portable directory rather than `%APPDATA%`.
> Need to create a `/portable` shortcut or clean up an accidental non-portable launch? See [FAQ Q1](#8-troubleshooting--faq).

### Step 2: Install `pea5`

Clone the repository and install `pea5` (using a standard virtual environment is recommended as an example):

- **PowerShell**:
  ```powershell
  git clone https://github.com/hjquantlab/portable-ea5-tester.git
  cd portable-ea5-tester
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install .
  ```
- **Command Prompt (`cmd.exe`)**:
  ```cmd
  git clone https://github.com/hjquantlab/portable-ea5-tester.git
  cd portable-ea5-tester
  python -m venv .venv
  .venv\Scripts\activate.bat
  pip install .
  ```

#### Trial / Direct Execution (No Installation)

Run directly from the repository root without installing into your Python environment:

- **Windows (PowerShell / Command Prompt)**:
  ```powershell
  python -m portable_ea5_tester --help
  ```

> **Note**: This direct execution method does not install anything into your system or virtual environment; the `pea5` command will not remain in your PATH once you close the terminal. It is intended for quick verification from the repository root. For regular usage, installing into a virtual environment as shown above is recommended.

<details>
<summary>Other Installation Options (uv / Global pip / Editable)</summary>

If you use other environment managers (such as `uv`, `conda`, or `poetry`), adapt the steps accordingly:

- **Using `uv`**:
  ```powershell
  uv venv .venv
  .\.venv\Scripts\Activate.ps1
  uv pip install .
  ```
- **Global `pip` install** (no virtual environment):
  ```powershell
  pip install .
  # If managed by system package manager:
  pip install --break-system-packages .
  ```
- **Editable / Developer install**:
  ```powershell
  pip install -e .
  ```

</details>

### Step 3: Configure & Run Smoke Test

Copy the example configuration file to create your local `config.json` and edit `terminal_dir` (and `expert`, `symbol`, etc.) as needed:

```powershell
copy config.example.json config.json
```

> **JSON Path Note**: Always use forward slashes `/` (e.g., `"C:/MT5-Portable"`) or escaped backslashes `\\` in JSON files. Single backslashes `\` cause JSON syntax errors.

#### Basic / Default Setup (No `credentials.json` Required)

For normal or interactive use, **you do not need `credentials.json`**. `pea5` automatically detects `Login` and `Server` from `<terminal_dir>/Config/common.ini` and uses MT5's cached password (pass `--offline` or set `"offline": true` in `config.json` when running purely on cached data).

Run the 4-command smoke test:

```powershell
# 1. Verify terminal, compiler, and detected account paths
pea5 init --config config.json

# 2. Launch MT5 GUI (/portable) once, log in with "Save password" checked to cache credentials & sync history, then close MT5
#    (Alternatively, use: .\scripts\launch_mt5_portable.bat)
pea5 login --config config.json

# 3. Compile an MQL5 EA (.mq5 -> .ex5)
pea5 compile --file "C:/MT5-Portable/MQL5/Experts/Examples/Moving Average/Moving Average.mq5" --terminal-dir "C:/MT5-Portable"

# 4. Run the sample backtest and export Markdown/CSV summaries
pea5 run --config config.json --export
```

> **Scheduled / Unattended Batch Runs**: MT5's saved password cache may reset or expire after several days. For periodic or unattended batch execution without manual re-login, placing `credentials.json` **outside the repository** at `~/.config/portable-ea5-tester/credentials.json` (or setting `PEA5_PASSWORD`) is recommended (see [7.4 Credentials](#74-credentials)).
> **Security Warning**: If you use `credentials.json`, never commit it to Git or paste its contents (`login`, `password`, `server`) into AI chats.

---

## 4. How It Works

### 4.1 `config.json` vs `.set` Files

- **`config.json`** controls *what* to run and *under what environment*: terminal paths, EA (`expert`), symbol, timeframe (`period`), date range (`from_date` / `to_date`), account settings (`deposit`, `currency`, `leverage`), execution/optimization mode (`model`, `optimization`, `optimization_criterion`), and report output options.
- **`.set` files** (optional) control *EA input parameters* (`input` variables inside the `.mq5` source): fixed overrides for a single backtest, or Start/Step/Stop ranges for parameter optimization.

### 4.2 EA Resolution & Compilation

The extension of `expert` decides whether `pea5 run` compiles the EA:

| `expert` value | Behavior |
| :--- | :--- |
| `.mq5` (e.g., `EA.mq5`) | **Always compiled** before testing, even if an `.ex5` already exists. The same `.mq5` is compiled only once per `pea5 run` (reused by later tasks). |
| `.ex5` (e.g., `EA.ex5`) | Used as-is. **Never compiled.** |
| No extension (e.g., `EA`) | Uses `EA.ex5` if found. Compiles `EA.mq5` only when no `.ex5` exists. |

- **Compile output location**: the `.ex5` is written **next to the source `.mq5`** (same folder, same base name). An existing `.ex5` there is overwritten.
- **Deployment**: the resolved `.ex5` is automatically copied to `<terminal_dir>/MQL5/Experts/`. You do not need to copy it manually.
- **Search order** for the file: the path as given → `<terminal_dir>/<path>` → `<terminal_dir>/MQL5/Experts/<file name>`.
- A compile with errors, or a compile that does not update the `.ex5`, stops the task with an error.

### 4.3 `.set` File Resolution

- `set_file` is **optional**. Omit it to use the EA default inputs.
- Relative paths are resolved from the current working directory; absolute paths are used as-is. The `.set` extension can be omitted.
- **Search order**: the path as given → `<terminal_dir>/<path>` → `<terminal_dir>/MQL5/Profiles/Tester/<file name>`.
- The found file is automatically copied to `<terminal_dir>/MQL5/Profiles/Tester/`.

---

## 5. Backtest & Optimization Patterns

### Pattern Selection Table

| Pattern | Use Case | `optimization` | `set_file` | Config Structure |
| :--- | :--- | :---: | :---: | :--- |
| **1. Single Backtest (Defaults)** | Quick baseline test with built-in EA defaults | `0` | Omitted | Single task |
| **2. Single Backtest (Custom Inputs)** | Test specific fixed EA parameters | `0` | Fixed `Key=Value` `.set` | Single task |
| **3. Parameter Optimization** | Grid or genetic sweep over 1 or more EA inputs | `1` or `2` | Sweep `Key=Val\|\|Start\|\|Step\|\|Stop\|\|Y` `.set` | Single task |
| **4. Multi-Task Batch Execution** | Vary symbol, timeframe, dates, mode, EA, `.set`, or account per task | `0`, `1`, or `2` per task | Optional per task | `common` + `tasks[]` |

### Pattern 1: Single Backtest (Default EA Parameters)

Omit `set_file` to run with the EA's compiled default inputs. Because `expert` points to a `.mq5` file, `pea5` compiles it before testing (see [4.2 EA Resolution & Compilation](#42-ea-resolution--compilation)).

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

> All task keys: see [7.2 `config.json` Parameters](#72-configjson-parameters).

### Pattern 2: Single Backtest with Custom Parameters

Specify `set_file` pointing to a standard MT5 `.set` file with `Key=Value` lines to override one or more EA inputs:

```ini
; presets/ma_custom.set
MaximumRisk=0.05
DecreaseFactor=3
MovingPeriod=24
MovingShift=2
```

> **Tip**: You can generate a `.set` file with exact parameter names directly from the MT5 Strategy Tester **Inputs** tab (right-click -> **Save**).

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

> All task keys: see [7.2 `config.json` Parameters](#72-configjson-parameters).

### Pattern 3: Parameter Optimization (Single- & Multi-Parameter Sweep)

MT5 optimization `.set` files use a 5-field syntax separated by `||`:

```ini
ParameterName=Value||Start||Step||Stop||Y/N
```

- **`||N`**: Parameter stays fixed at `Value` (not optimized).
- **`||Y`**: Parameter is swept from `Start` to `Stop` in increments of `Step`.
  - **Single-parameter optimization**: Set `||Y` on **1 parameter** and `||N` on all others.
  - **Multi-parameter simultaneous optimization**: Set `||Y` on **2 or more parameters**. MT5 evaluates combinations across all enabled parameters (e.g., `5 × 5 × 11 = 275` combinations below):

```ini
; presets/ma_optimize.set
MaximumRisk=0.02||0.01||0.01||0.05||Y
DecreaseFactor=3||1||1||5||Y
MovingPeriod=12||10||2||30||Y
MovingShift=0||0||1||10||N
```

Set `optimization` in `config.json`:
- `1`: **Complete (Slow)** — evaluates every combination.
- `2`: **Genetic Algorithm (Fast)** — recommended for large multi-parameter spaces.

Set `optimization_criterion` (`0`–`6`):
- `0`: Balance max | `1`: Profit Factor max | `2`: Expected Payoff max | `3`: Drawdown min | `4`: Recovery Factor max | `5`: Sharpe Ratio max | `6`: Custom max (`OnTester()`)

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

> All task keys: see [7.2 `config.json` Parameters](#72-configjson-parameters).

### Pattern 4: Multi-Task Batch Execution (`common` + `tasks`)

`tasks[]` is **not** limited to switching `.set` files. Shared defaults go in `common`, and **each task in `tasks[]` can independently override any test condition**: timeframe (`period`), date range (`from_date` / `to_date`), execution mode (`optimization`, `optimization_criterion`, `model`), `symbol`, `expert`, `set_file`, and account settings (`deposit`, `leverage`).

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

Run all tasks in sequence, or run a single task by its zero-based index:

```powershell
# Run all 3 tasks
pea5 run --config config.json

# Run only task index 0 (first task)
pea5 run --config config.json --task 0
```

> All task keys: see [7.2 `config.json` Parameters](#72-configjson-parameters).

---

## 6. Output Reports

| Execution Type | Generated Artifacts (in `report_dir`) | Notes |
| :--- | :--- | :--- |
| **Single Backtest** (`optimization: 0`) | `<ReportName>.html`, `<ReportName>.json`, `*.png` | `*.png` charts kept when `output_formats.keep_charts` and `output_formats.html` are `true`. |
| **Single Backtest + `--export`** | Adds `<ReportName>_report.md`, `<ReportName>_trades.csv`, `<ReportName>_metrics.json` | Clean Markdown & compact CSV for notebooks/LLM analysis. |
| **Optimization** (`optimization > 0`) | `<ReportName>.xml`, `<ReportName>.html`, `<ReportName>.json` | `.html` is the generated Optimization Dashboard; `.json` includes `passes` and `best_pass`. |
| **Batch Summary** (every `pea5 run`) | `batch_summary.html`, `batch_summary.json` | Aggregated dashboard and JSON summary written to the report directory. |

> Output folder, file names, and placeholders: see [7.3 Report Naming Options](#73-report-naming-options).

---

## 7. Reference

### 7.1 CLI Subcommands

| Command | Purpose | Key Options |
| :--- | :--- | :--- |
| `pea5 setup` | Generate `launch_mt5_portable.bat` inside the portable MT5 folder | `<target>` (positional path to MT5 folder or `terminal64.exe`), `--terminal-dir` / `-d`, `--config` / `-c`, `--force` / `-f` (alias: `setup-launcher`) |
| `pea5 init` | Verify `config.json`, MT5 terminal, MetaEditor, and credentials | `--config` / `-c` (default: `config.json`) |
| `pea5 login` | Launch MT5 GUI (`/portable`) with pre-filled Login/Server to cache credentials | `--config` / `-c` (default: `config.json`) |
| `pea5 compile` | Headless `.mq5` -> `.ex5` compilation via `metaeditor64.exe` | `--file` / `-f` (required), `--compiler`, `--terminal-dir` (automatically adds `/inc:<terminal_dir>/MQL5`), `--include` / `-i` (optional external include root outside `<terminal_dir>/MQL5`), `--timeout` (default: `60`) |
| `pea5 run` | Execute backtest or optimization tasks (auto-compiles .mq5 targets) | `--config` / `-c` (default: `config.json`), `--task` / `-t`, `--offline`, `--timeout`, `--export` / `-e`, `--no-open-report` |

> **`pea5 compile` output & include behavior**: The `.ex5` binary is written next to the `--file` source (same folder, same base name). Specifying `--terminal-dir` automatically adds `/inc:<terminal_dir>/MQL5` to the MetaEditor include path. The `--include` option is optional, used only when custom external header directories outside `<terminal_dir>/MQL5` are needed. Note that `pea5 compile` does not copy the `.ex5` into `<terminal_dir>/MQL5/Experts/`; `pea5 run` handles that deployment automatically.
>
> **Manual MetaEditor Execution**: When running `metaeditor64.exe` manually outside `pea5`, always pass `/portable` (e.g., `C:\MT5-Portable\metaeditor64.exe /portable`) to ensure data stays within the portable directory rather than `%APPDATA%`.

### 7.2 `config.json` Parameters

#### `terminal` Section

| Key | Description |
| :--- | :--- |
| `directory` | Path to portable MT5 root folder (also supports flat `terminal_dir`). |
| `executable` | Explicit path to `terminal64.exe` (optional if `directory` is set). |
| `compiler` | Explicit path to `metaeditor64.exe` (optional if `directory` is set). |

#### `common` / `tasks[]` Section

| Key | Default | Description |
| :--- | :--- | :--- |
| `expert` | *Required* | Path or name of the EA (`.mq5`, `.ex5`, or no extension). See [4.2](#42-ea-resolution--compilation). |
| `symbol` | *Required* | Broker symbol name (e.g., `"EURUSD"`). |
| `period` | *Required* | Chart timeframe (`M1`, `M5`, `M15`, `M30`, `H1`, `H4`, `D1`, `W1`, `MN1`). |
| `from_date` | *Required* | Start date (`YYYY.MM.DD` or `YYYY-MM-DD`). |
| `to_date` | *Required* | End date (`YYYY.MM.DD` or `YYYY-MM-DD`). |
| `set_file` | `null` | Optional path to `.set` preset file. See [4.3](#43-set-file-resolution). |
| `model` | `0` | Tick model: `0` (Every tick), `1` (1 minute OHLC), `2` (Open prices only), `3` (Math calculations), `4` (Every tick based on real ticks). |
| `optimization` | `0` | `0` (Disabled), `1` (Complete), `2` (Genetic), `3` (All symbols in Market Watch). |
| `optimization_criterion` | `0` | `0`–`6` (Balance, Profit Factor, Expected Payoff, Drawdown min, Recovery Factor, Sharpe Ratio, Custom `OnTester`). |
| `execution_mode` | `0` | Execution delay in ms (`0` = no delay, `-1` = random delay). |
| `deposit` | `10000` | Initial account deposit. |
| `currency` | `"USD"` | Account deposit currency. |
| `leverage` | `50` (`100` in `config.example.json`) | Account leverage (`1:N` as integer `N`). |
| `shutdown_terminal` | `true` | Close MT5 automatically when test completes. |
| `offline` | `false` | Skip strict credential error if password is omitted. |
| `timeout` | `600` | Process timeout in seconds per task. |
| `heartbeat_interval` | `10.0` | Console progress heartbeat interval in seconds. |
| `min_history_quality` | `90.0` | Threshold (%) below which a low-data-quality warning is printed. |
| `output_formats` | `{ "html": true, "json": true, "keep_charts": true, "batch_summary_json": true }` | Toggle generated HTML, JSON, chart `.png`s, and `batch_summary.json` (configured in `common`). |

### 7.3 Report Naming Options

Configure these keys in `common` or per task in `tasks[]`:

| Key | Default | Description |
| :--- | :--- | :--- |
| `report_dir` | `"reports"` | Output directory (relative to `config.json` or absolute). |
| `report_name` | Auto (`Report_<symbol>_<period>[_<set>][_opt]`) | Custom filename template (extension added automatically; `_t1`, `_t2` appended in multi-task runs if omitted). |
| `use_subfolder` | `false` | When `true`, creates a subfolder under `report_dir`. |
| `folder_template` | `"{date}_{ea}"` | Subfolder name template when `use_subfolder` is `true`. |
| `auto_increment` | `false` | Appends `_01`, `_02`, ... if the target report file already exists. |
| `subfolder_auto_increment` | Same as `auto_increment` | Appends `_01`, `_02`, ... if the target subfolder already exists. |

**Supported Placeholders** (for `report_name` and `folder_template`):

| Placeholder | Value | Example |
| :--- | :--- | :--- |
| `{datetime}` | `YYYYMMDD_HHMMSS` | `20261116_143022` |
| `{date}` | `YYYYMMDD` | `20261116` |
| `{time}` | `HHMMSS` | `143022` |
| `{ea}` | EA base filename (sanitized) | `Moving Average` |
| `{symbol}` | Symbol name | `EURUSD` |
| `{period}` | Timeframe | `H1` |
| `{set}` | `.set` base filename, or `"default"` | `ma_custom` |
| `{type}` | `"opt"` if `optimization > 0`, else `"test"` | `test` |

#### Concrete Configuration Example

```json
{
  "common": {
    "use_subfolder": true,
    "folder_template": "{date}_{ea}",
    "report_name": "Report_{symbol}_{period}_{set}"
  }
}
```

If executed on `2026-03-30` for EA `Moving Average` on `USDJPY` `H1` with `set1.set`, the generated report path will be:

```
reports/20260330_Moving Average/Report_USDJPY_H1_set1.html
```

### 7.4 Credentials

`pea5` supports a two-tier authentication model depending on how you run your tests:

- **Basic / Interactive Use (No `credentials.json` required)**: `pea5` automatically detects `Login` and `Server` from `<terminal_dir>/Config/common.ini` and relies on MT5's cached password saved when you log in via `pea5 login --config config.json` (or `.\scripts\launch_mt5_portable.bat`) with **"Save password"** checked. Use `--offline` (or `"offline": true` in `config.json`) when running purely on cached data.
- **Scheduled / Unattended Batch Runs (`credentials.json` recommended)**: MT5's saved password cache may reset or expire after several days. For periodic or unattended batch runs without manual re-login, store `credentials.json` **outside the repository** at `~/.config/portable-ea5-tester/credentials.json` (or provide `PEA5_PASSWORD`). Note that if a demo account expires or the broker requires 2FA/OTP or a password change, manual re-authentication is still required.

> **Security Warning**: Never commit `credentials.json` to Git or paste its contents (`login`, `password`, `server`) into AI chats.

#### `credentials.json` Schema (Optional / For Unattended Batch Runs)

```powershell
mkdir "$HOME\.config\portable-ea5-tester" -Force
copy credentials.example.json "$HOME\.config\portable-ea5-tester\credentials.json"
```

```json
{
  "login": 12345678,
  "password": "your_password",
  "server": "Broker-DemoServer"
}
```

#### Resolution Priority Order

1. `config.json` (`credentials` object, `credentials_file` path, or `./credentials.json` next to `config.json`)
2. Active MT5 terminal `<terminal_dir>/Config/common.ini` (`Login` and `Server` auto-detection)
3. User home config (`~/.config/portable-ea5-tester/credentials.json`, fallback `~/.config/portable-strategy-tester/credentials.json`)
4. Environment variables (`PEA5_LOGIN`, `PEA5_PASSWORD`, `PEA5_SERVER`, fallback `PST_LOGIN`, `PST_PASSWORD`, `PST_SERVER`)

> **Note on `--offline` (No `credentials.json` / No `password`)**: Even in offline mode, `login` and `server` are **still required** so MT5 can locate broker history under `bases/<ServerName>/` and symbol specifications. When `Login` and `Server` are already present in `<terminal_dir>/Config/common.ini` and your password is cached via `pea5 login` (with "Save password" checked), you can run `pea5 run --offline` without `credentials.json` or `password`.

---

## 8. Troubleshooting & FAQ

<details>
<summary>Q1: I accidentally launched terminal64.exe without /portable, or want a safe shortcut</summary>

1. **Use the safe launcher generator or create a `/portable` shortcut**:
   - First run `python -m portable_ea5_tester setup "<path-to-mt5>"` (or `pea5 setup "<path-to-mt5>"`) to generate `launch_mt5_portable.bat` inside your MT5 portable folder.
   - Then double-click or run `launch_mt5_portable.bat` inside that folder to verify the exact `terminal64.exe` path and launch it with `/portable` only after `y/n` confirmation.
   - Or create a Windows shortcut: right-click `terminal64.exe` inside your portable MT5 directory (e.g., `C:\MT5-Portable\terminal64.exe`) -> **Create shortcut**, then right-click the shortcut -> **Properties** -> append ` /portable` to **Target** (e.g., `"C:\MT5-Portable\terminal64.exe" /portable`).
2. **Clean up an accidental non-portable launch (`origin.txt` mechanism)**:
   - When MT5 is launched in standard (non-portable) mode, it creates a 32-character hexadecimal hash folder under `%APPDATA%\MetaQuotes\Terminal\<hash>\`. Inside that folder, `origin.txt` records the exact installation directory (e.g. `D:\Trading\MT5_Main` or `C:\Program Files\MetaTrader 5`) that generated that specific hash directory (`C:\MT5-Portable` is merely an example path).
   - **Safe cleanup procedure**:
     1. Close all MT5 instances and open `%APPDATA%\MetaQuotes\Terminal\` in File Explorer.
     2. Check `origin.txt` inside each 32-character hash directory to see which MT5 directory created it.
     3. Only remove the folder if its `origin.txt` points to the portable MT5 directory that was accidentally started without `/portable`.
     4. Do **NOT** delete folders whose `origin.txt` corresponds to your regular installed MT5 terminals.

</details>

<details>
<summary>Q2: pea5 compile fails with missing include files (.mqh) or MetaEditor opens interactively</summary>

- **Missing `.mqh` headers**: Specifying `--terminal-dir` automatically adds `/inc:<terminal_dir>/MQL5` to the MetaEditor include search path. Use the optional `--include` flag when you need custom external header directories outside `<terminal_dir>/MQL5`:
  1. **Standard compilation** (using terminal standard libraries; MetaEditor automatically includes `C:/MT5-Portable/MQL5`):
     ```powershell
     pea5 compile --file Experts/MyEA.mq5 --terminal-dir "C:/MT5-Portable"
     ```
  2. **Custom compilation with external include root**:
     ```powershell
     pea5 compile --file Experts/MyEA.mq5 --terminal-dir "C:/MT5-Portable" --include "C:/SharedMQL5"
     ```
- **MetaEditor opens GUI or uses `%APPDATA%`**: Always ensure `metaeditor64.exe` resides in your portable MT5 folder. When launching MetaEditor manually or creating a shortcut, always pass `/portable` (e.g., `C:\MT5-Portable\metaeditor64.exe /portable`), otherwise it will access standard roaming `%APPDATA%` instead of your portable directory.

</details>

<details>
<summary>Q3: Backtest finishes with 0 trades, [AGENT SYNC ERROR], [MISSING HISTORY DATA], or [INVALID SYMBOL ERROR]</summary>

- **`[AGENT SYNC ERROR]` / `[ACCOUNT SETUP REQUIRED]`**: Run `pea5 login --config config.json`, enter your password, check **Save password**, click **OK**, and close MT5.
- **`[MISSING HISTORY DATA]` / Low `min_history_quality`**: Open a chart for the target symbol/timeframe in `C:\MT5-Portable\terminal64.exe /portable` (or scroll back in Strategy Tester / History Center) to download M1 history for the requested date range.
- **`[INVALID SYMBOL ERROR]`**: Check your broker's exact symbol suffix in MT5 Market Watch (e.g., `EURUSD.m`, `EURUSDpro`, `EURUSD#`) and match it in `config.json`.
- **0 trades with valid history**: Verify EA logic, spread/lot constraints, and `.set` parameter ranges.

</details>

---

## 9. Maintenance & Support Policy

- **As-Is Provision**: This tool is provided **As-Is** under the MIT License without warranty or guaranteed support of any kind.
- **Scope & Limitations**: The project is maintained primarily for internal quantitative research and automation workflows. Individual troubleshooting, custom feature development, and assistance with external platforms (such as Wine/macOS) are out of scope.
- **Contact**: For vulnerability disclosures or critical inquiries, reach out to `hjquantlab@gmail.com`.

## 10. License

MIT License — Copyright (c) 2026 hjQuantLab. See [LICENSE](LICENSE) for details.
