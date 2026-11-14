# Portable Strategy Tester (`portable-ea5-tester`)

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[English](README.md) | [日本語](README.ja.md)

**Portable Strategy Tester** (`pea5`) is a lightweight, standalone, and portable CLI framework for compiling MetaTrader 5 Expert Advisors (`.mq5` to `.ex5`) and running automated backtests or optimizations. The "Portable" in its name primarily refers to targeting **Portable MetaTrader 5** (`/portable` mode), in addition to the tool itself being zero-dependency and portable.

> **Important**: `portable-ea5-tester` **only works with MetaTrader 5 running in `/portable` mode**. It does **not** support standard MetaTrader 5 installations where program files and user data are split into `%APPDATA%`.

---

## Key Features

- **Zero External Dependencies**: Built strictly on the Python standard library (`dependencies = []`).
- **Headless & Portable Execution**: Automate MT5 compilation (`metaeditor64.exe`) and backtesting (`terminal64.exe /portable`) via JSON configuration files and the `pea5` CLI.
- **Automated Report Generation**: Parse MT5 Strategy Tester reports into a `batch_summary.html` dashboard and export Markdown / compact CSV summaries (`--export`).

---

## Prerequisites

- **OS**: Windows 10 / 11 (required for MetaTrader 5 terminal and MetaEditor).
- **Python**: Python 3.9 or higher.
- **MetaTrader 5**: A portable MetaTrader 5 directory containing `terminal64.exe` and `metaeditor64.exe`.

---

## Step 1: Portable MT5 Setup (3-Step Guide)

> **Important**: `portable-ea5-tester` **only supports Portable MT5 (`/portable` mode)** and does **not** work with standard MT5 installations where data is split into `%APPDATA%`. Follow the steps below to set up a self-contained portable MT5 directory.

1. **Install Standard MetaTrader 5**: Download and run the MetaTrader 5 installer from MetaQuotes or your broker (if not already installed).
2. **Create a Dedicated Portable Folder & Copy Executables**: Create a dedicated folder such as `C:\MT5-Portable`, and copy `terminal64.exe` and `metaeditor64.exe` from your standard installation (e.g., `C:\Program Files\MetaTrader 5`) into `C:\MT5-Portable`.
3. **Initialize Portable Mode Once**: Launch `C:\MT5-Portable\terminal64.exe` once with the `/portable` flag:
   ```powershell
   C:\MT5-Portable\terminal64.exe /portable
   ```
   MT5 will automatically extract `MQL5/` (including built-in sample EAs) and `Config/` inside `C:\MT5-Portable`. Once MT5 opens, close it and proceed to Step 2.

> **Warning**: **Even after setup is complete**, double-clicking `terminal64.exe` (or `metaeditor64.exe`) directly without `/portable` launches MT5 in normal mode and creates/uses a separate `%APPDATA%\MetaQuotes\Terminal\<32-char-hash>\` folder instead of `C:\MT5-Portable`. To prevent accidental normal-mode launches, we recommend creating a `/portable` shortcut inside `C:\MT5-Portable` (or on your Desktop) and launching from it, or using `pea5 login` / `pea5 run` (which pass `/portable` automatically). See the [FAQ](#faq) for shortcut creation steps, `origin.txt` verification, and cleanup instructions.

---

## Step 2: Install `portable-ea5-tester`

Clone the repository and enter the project directory:

```powershell
git clone https://github.com/hjquantlab/portable-ea5-tester.git
cd portable-ea5-tester
```

### Option A: Install with `pip` (Recommended)

Create and activate a virtual environment (`.venv`), then install the zero-dependency Python package locally. This registers the `pea5` CLI command (along with `portable-ea5-tester` and `pst-runner` aliases) inside your virtual environment:

- **PowerShell**:
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install .
  ```
- **Command Prompt (`cmd`)**:
  ```cmd
  python -m venv .venv
  .venv\Scripts\activate.bat
  pip install .
  ```

> **Note**:
> - If you prefer installing directly into your global Python environment, you can skip the `venv` steps above and run `pip install .` directly.
> - **`uv` users**: You can also use `uv venv` + `uv pip install .`, or install `pea5` globally as a CLI tool with `uv tool install .`.

For development (includes `pytest`):

```powershell
pip install -e ".[dev]"
```

### Option B: Quick Trial Without Installing (`PYTHONPATH`)

For a quick trial or temporary use without installing, you can run `portable_ea5_tester/` directly from the repository root by setting `PYTHONPATH` to `.`:

- **PowerShell**:
  ```powershell
  $env:PYTHONPATH = "."
  python -m portable_ea5_tester --help
  ```
- **Command Prompt (`cmd`)**:
  ```cmd
  set PYTHONPATH=.
  python -m portable_ea5_tester --help
  ```

> **Note**:
> - Setting `$env:PYTHONPATH = "."` / `set PYTHONPATH=.` is **temporary for the current terminal session only** and resets as soon as you close the terminal window (you must re-run it if you open a new terminal). See the [FAQ](#faq) for details.
> - When using Option B, replace `pea5 <subcommand>` in the examples below with `python -m portable_ea5_tester <subcommand>`.

---

## Step 3: Step-by-Step Quick Start

### 1. Create Configuration Files

Copy the example templates to your working config files:

- **PowerShell**:
  ```powershell
  Copy-Item config.example.json config.json
  Copy-Item credentials.example.json credentials.json
  ```
- **Command Prompt (`cmd`)**:
  ```cmd
  copy config.example.json config.json
  copy credentials.example.json credentials.json
  ```

### 2. Edit `config.json` and `credentials.json`

`config.example.json` uses Windows absolute paths with forward slashes `/` (e.g., `C:/MT5-Portable/terminal64.exe`). Update the paths if your portable MT5 folder is in a different location.

> **JSON Path Syntax Note**:
> - In JSON on Windows, a single backslash `\` causes a JSON parse error. Always use forward slashes `/` (recommended, e.g., `"C:/MT5-Portable"`) or escaped backslashes `\\` (e.g., `"C:\\MT5-Portable"`).
> - Relative paths (e.g., `"./mt5_terminal"`, resolved relative to the directory containing `config.json`) are also supported if you place MT5 inside the project folder.

Edit `credentials.json` with your MT5 demo/live account `login`, `password`, and `server` name.

### 3. Verify Your Setup (Smoke Test)

Run this one-time verification test with MT5's built-in sample EA to confirm your environment works end-to-end before testing your own EA:

1. **Verify your environment (`pea5 init`)**:  
   **Purpose**: Verify `config.json`, MT5 paths, and compiler detection before running anything.
   ```powershell
   pea5 init --config config.json
   ```
2. **Cache broker credentials in MT5 (`pea5 login`)**:  
   **Purpose**: Cache broker credentials in Portable MT5 so automated tests do not stall on login prompts.
   ```powershell
   pea5 login --config config.json
   ```
   This launches MT5 GUI in portable mode with your login/server pre-filled. Enter your password if prompted, check **Save password**, click **OK**, and close MT5 to complete the command.
3. **Compile a built-in MT5 sample EA (`pea5 compile`)**:  
   **Purpose**: Confirm `metaeditor64.exe` compilation works using MT5's built-in sample EA before compiling your own EA.
   ```powershell
   pea5 compile --file "C:/MT5-Portable/MQL5/Experts/Examples/Moving Average/Moving Average.mq5" --terminal-dir C:/MT5-Portable
   ```
   > **Note**: For `.mqh` include resolution (`--include`) and troubleshooting compile errors in the MetaEditor GUI, see the [FAQ](#faq).
4. **Run the backtest and export reports (`pea5 run`)**:  
   **Purpose**: Confirm end-to-end Strategy Tester execution and report generation.
   ```powershell
   pea5 run --config config.json --export
   ```

---

## CLI Reference

| Command | Description & Options |
| :--- | :--- |
| `pea5 init [--config config.json]` | Diagnostic wizard to verify `config.json`, MT5 terminal/compiler paths, and credentials. (`-c` / `--config`, default: `config.json`) |
| `pea5 login [--config config.json]` | Launches MT5 GUI in `/portable` mode pre-filled with `Login` and `Server` to cache credentials. (default `--config`: `tester_config.json`, so pass `--config config.json`) |
| `pea5 compile --file <path.mq5> [options]` | Compiles an `.mq5` source file into `.ex5` via MetaEditor.<br>Options: `-f` / `--file` (required), `--compiler <metaeditor64.exe>`, `--terminal-dir <dir>`, `-i` / `--include <dir>`, `--timeout <sec>` (default: `60`). |
| `pea5 run [--config config.json] [options]` | Executes backtest or optimization tasks from `config.json`.<br>Options: `-c` / `--config` (default: `config.json`), `-t` / `--task <index>` (0-based), `--offline`, `--timeout <sec>`, `-e` / `--export` (export Markdown & compact CSV), `--open-report` / `--no-open-report` (auto-open `batch_summary.html` in browser; default: `--open-report`). |

> **Note on `pea5 compile` Include Paths (`.mqh`)**:
> - If `--include` (`-i`) is omitted and `--terminal-dir` is provided, `pea5 compile` automatically passes `<terminal_dir>/MQL5` to MetaEditor as `/inc:` (if that directory exists), enabling standard `#include <...>` headers under `MQL5/Include/`.
> - If your `.mqh` files reside outside `<terminal_dir>/MQL5`, pass `--include <dir>` (e.g., `pea5 compile -f C:/MyEAs/MyEA.mq5 --terminal-dir C:/MT5-Portable -i C:/MyEAs/Include`). Note that specifying `--include` overrides the automatic `<terminal_dir>/MQL5` `/inc:` path.

---

## Configuration & Credentials Reference

### `config.json` Schema

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

- `terminal`: Specifies `directory`, `executable`, and `compiler`.
- `tasks`: List of backtest tasks. Optional task fields include `set_file`, `model`, `optimization`, `optimization_criterion`, `execution_mode`, `offline`, `timeout`, `report_name`, and `shutdown_terminal`. Shared defaults can also be placed in a top-level `"common": { ... }` object.
- `tasks[].expert`: Accepts an absolute path, a path relative to `terminal.directory` (e.g., `MQL5/Experts/Examples/Moving Average/Moving Average.ex5`), or an `.mq5` path (automatically compiled if `.ex5` is missing).

#### Multi-Task Batch Example

`"common"` sets shared defaults, while each item in `"tasks"` can override **any** setting — allowing you to mix multiple EAs (`expert`), symbols (`symbol`), timeframes (`period`), date ranges (`from_date` / `to_date`), preset files (`set_file`), and backtest/optimization modes (`optimization`) in a single batch run:

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

- **How `"common"` & `"tasks"` merge**: For each entry in `"tasks"`, `"common"` is loaded as the base dictionary and overridden by any task-specific keys.
- **How `set_file` works**: Each `.set` file is automatically copied to `<terminal_dir>/MQL5/Profiles/Tester/` before the task starts, and its filename is passed to MT5 Strategy Tester (`ExpertParameters` / `Parameters`).
- **Running all vs. a single task**:
  - `pea5 run --config config.json` runs all tasks sequentially (auto-appending `_t1`, `_t2`, ... to report filenames when `report_name` is omitted).
  - `pea5 run --config config.json --task 0` (or `--task 1`) runs only the specified 0-based task index.

#### Optimization Testing (`optimization`)

`pea5` also supports MT5 Strategy Tester parameter optimization via task-level (or `common`) fields in `config.json`:

- `optimization` (default: `0`): `0` = single backtest (disabled), `1` = slow complete algorithm, `2` = fast genetic algorithm.
- `optimization_criterion` (default: `0`): Optimization target criterion passed to MT5 when `optimization > 0` (e.g., `0` = Balance max, `1` = Profit Factor max, `2` = Expected Payoff max, `6` = Custom max).
- `model` (default: `0`): Tick generation mode (`0` = Every tick, `1` = 1 minute OHLC, `2` = Open prices only, `3` = Math calculations, `4` = Every tick based on real ticks).

> **Note**: Parameter optimization ranges (**Start / Step / Stop**) are defined inside the `.set` file referenced by `set_file`, while `config.json` enables optimization mode and selects the criterion.

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

### `credentials.json` Schema & Precedence

```json
{
  "login": 12345678,
  "password": "your_password",
  "server": "Broker-DemoServer"
}
```

Credentials are resolved in the following strict order:

1. `credentials` object in `config.json`, `credentials_file` path in `config.json`, or `./credentials.json` in the same directory as `config.json`.
2. Auto-detection from `<terminal_dir>/Config/common.ini` (`Login` and `Server`).
3. User home config: `~/.config/portable-ea5-tester/credentials.json` (fallback: `~/.config/portable-strategy-tester/credentials.json`).
4. Environment variables: `PEA5_LOGIN`, `PEA5_PASSWORD`, `PEA5_SERVER` (fallback: `PST_LOGIN`, `PST_PASSWORD`, `PST_SERVER`).

> **Note**: Even in `--offline` mode, MT5 Strategy Tester requires `login` and `server` to locate broker history in `bases/<ServerName>/` and symbol specifications (`password` is optional for offline testing).

---

## FAQ

### Q1: I accidentally launched MT5 without `/portable` and `%APPDATA%\MetaQuotes\Terminal\<32-char-hash>\` was created. What should I do?

**Even after initial setup is complete**, double-clicking `terminal64.exe` (or `metaeditor64.exe`) directly without the `/portable` flag launches MT5 in normal mode and creates/uses a separate data folder under `%APPDATA%\MetaQuotes\Terminal\<32-char-hash>\` instead of `C:\MT5-Portable`.

To verify and clean it up safely:
1. Close MT5 completely.
2. Open `%APPDATA%\MetaQuotes\Terminal\<32-char-hash>\origin.txt` in a text editor and check that it points to your portable folder (e.g., `C:\MT5-Portable`).
3. Once confirmed, it is safe to delete that `<32-char-hash>` folder while MT5 is closed (your portable data inside `C:\MT5-Portable` is unaffected).
4. Going forward, always launch manually with `/portable` (via a `/portable` shortcut) or use `pea5 login` / `pea5 run`.

**How to create a `/portable` shortcut:**

- **Windows Explorer (GUI)**:
  1. Right-click `C:\MT5-Portable\terminal64.exe` and select **Create shortcut** (keep it inside `C:\MT5-Portable` or move it to your Desktop).
  2. Right-click the created shortcut and select **Properties**.
  3. In **Target**, append ` /portable` at the end (e.g., `"C:\MT5-Portable\terminal64.exe" /portable`) and click **OK**.
  4. *(Optional)* Repeat the same steps for `metaeditor64.exe` if needed.
- **PowerShell**:
  ```powershell
  $ws = New-Object -ComObject WScript.Shell
  $sc = $ws.CreateShortcut("C:\MT5-Portable\MT5-Portable.lnk")
  $sc.TargetPath = "C:\MT5-Portable\terminal64.exe"
  $sc.Arguments = "/portable"
  $sc.WorkingDirectory = "C:\MT5-Portable"
  $sc.Save()
  ```
- **Command Prompt (`cmd`)**:
  ```cmd
  powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut('C:\MT5-Portable\MT5-Portable.lnk'); $sc.TargetPath = 'C:\MT5-Portable\terminal64.exe'; $sc.Arguments = '/portable'; $sc.WorkingDirectory = 'C:\MT5-Portable'; $sc.Save()"
  ```

### Q2: `pea5 compile` fails (e.g., missing `.mqh` include or MQL5 syntax/API errors). How do I troubleshoot?

- **`.mqh` include resolution**: When `--terminal-dir` is specified and `--include` (`-i`) is omitted, `pea5 compile` automatically detects `<terminal_dir>/MQL5` and passes it to MetaEditor via `/inc:`. If your `.mqh` files are outside `<terminal_dir>/MQL5`, pass `--include` (`-i`) explicitly (e.g., `pea5 compile --file "C:/MyEAs/MyStrategy.mq5" --terminal-dir C:/MT5-Portable --include C:/MyEAs/Include`).
- **Inspecting full compiler errors**: Launch MetaEditor in portable mode:
  ```powershell
  C:\MT5-Portable\metaeditor64.exe /portable
  ```
  Open and compile the `.mq5` file in the MetaEditor GUI to view full error messages and exact line numbers in the **Toolbox** tab.

### Q3: I get a JSON parse error when writing Windows paths in `config.json`.

In JSON on Windows, a single backslash `\` is treated as an escape character and causes a JSON parse error. Always use forward slashes `/` (recommended, e.g., `"C:/MT5-Portable"`) or escaped backslashes `\\` (e.g., `"C:\\MT5-Portable"`).

### Q4: How do I run without `pip install`, or why is `pea5` not found in a new terminal?

- **Temporary run (`PYTHONPATH`)**: Setting `$env:PYTHONPATH = "."` (PowerShell) or `set PYTHONPATH=.` (`cmd`) lets you run `python -m portable_ea5_tester <subcommand>` without installing, but this setting is **temporary for the current terminal session only** and resets when you close the terminal window.
- **Persistent CLI (`pip install`)**: For regular use, create/activate `.venv` and run `pip install .` (Option A in Step 2) so `pea5` is available whenever `.venv` is activated.

### Q5: How can I run multiple EAs, symbols, `.set` presets, or backtest/optimization modes in one batch?

Place shared defaults in `"common"` and override **any** setting per entry in `"tasks"` — including `expert`, `symbol`, `period`, `from_date` / `to_date`, `set_file`, and `optimization` (see the [Multi-Task Batch Example](#multi-task-batch-example) above).
- Run all tasks sequentially: `pea5 run --config config.json`
- Run a single task by 0-based index: `pea5 run --config config.json --task 0` (or `--task 1`)

---

## Maintenance & Support Policy

- **As-Is Provision**: This project is provided as-is without dedicated customer support or guaranteed SLAs.
- **Bug Reports**: Bug reports, inquiries, and feedback can be sent to `hjquantlab@gmail.com` on a best-effort basis (no guaranteed response or SLA).
- **Future Development & Pro Edition**: User feedback, GitHub Stars, and community reception will directly determine future development roadmap priorities and decisions regarding the Pro Edition.

---

## License

This project is licensed under the [MIT License](LICENSE).  
Copyright (c) 2026 hjQuantLab — [https://github.com/hjquantlab/portable-ea5-tester](https://github.com/hjquantlab/portable-ea5-tester)
