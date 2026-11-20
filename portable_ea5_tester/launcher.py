"""
Portable MT5 Launcher & Setup Tool.

Generates `launch_mt5_portable.bat` inside a portable MetaTrader 5 directory
so users can safely launch `terminal64.exe /portable` after explicit confirmation.
Standard library only. Pure ASCII output.
"""

import os
from typing import Optional

try:
    from .config_resolver import load_config, resolve_terminal
except ImportError:
    from portable_ea5_tester.config_resolver import load_config, resolve_terminal


LAUNCH_MT5_PORTABLE_BAT = r"""@echo off
setlocal

set "TARGET_EXE="

if exist "%~dp0terminal64.exe" (
    for %%I in ("%~dp0terminal64.exe") do set "TARGET_EXE=%%~fI"
    goto :confirm_launch
)

if "%~1"=="" (
    echo [ERROR] terminal64.exe not found in: "%~dp0"
    exit /b 1
)

call :resolve_candidate "%~1"
if not defined TARGET_EXE (
    echo [ERROR] terminal64.exe not found at specified path: "%~1"
    exit /b 1
)

:confirm_launch
echo Found: %TARGET_EXE%
set "CONFIRM="
set /p "CONFIRM=Launch with /portable mode? Are you OK? (y/n): "
if /i "%CONFIRM%"=="y" (
    echo [LAUNCH] Starting "%TARGET_EXE%" /portable
    start "" "%TARGET_EXE%" /portable
    exit /b 0
)

echo [ABORT] Launch cancelled by user.
exit /b 0

:resolve_candidate
set "CAND=%~1"
if "%CAND%"=="" goto :eof
if exist "%CAND%\terminal64.exe" (
    for %%I in ("%CAND%\terminal64.exe") do set "TARGET_EXE=%%~fI"
    goto :eof
)
if exist "%CAND%" (
    if /i "%~nx1"=="terminal64.exe" (
        for %%I in ("%CAND%") do set "TARGET_EXE=%%~fI"
    )
)
goto :eof
"""


def resolve_mt5_target_dir(
    terminal_dir: Optional[str] = None,
    config_path: Optional[str] = None,
) -> str:
    """
    Resolves the target portable MT5 directory containing terminal64.exe.

    If `terminal_dir` is provided, strips surrounding quotes, normalizes the path,
    accepts either the directory or a direct path to `terminal64.exe`, and verifies
    that `terminal64.exe` exists inside the resolved directory.

    Otherwise, attempts to load `config_path` (if it exists) and resolve the
    terminal directory via `resolve_terminal`.

    Raises FileNotFoundError if `terminal64.exe` cannot be found.
    """
    if terminal_dir is not None and terminal_dir.strip():
        cleaned = terminal_dir.strip().strip('"').strip("'").strip()
        if not cleaned:
            raise FileNotFoundError("Empty terminal directory path provided.")
        norm = os.path.abspath(os.path.normpath(os.path.expanduser(cleaned)))
        if os.path.basename(norm).lower() == "terminal64.exe":
            target_dir = os.path.dirname(norm)
        else:
            target_dir = norm
        exe_path = os.path.join(target_dir, "terminal64.exe")
        if not os.path.isfile(exe_path):
            raise FileNotFoundError(
                f"terminal64.exe not found in specified directory: {target_dir}"
            )
        return target_dir

    cfg = None
    base_dir = "."
    if config_path and os.path.exists(config_path):
        cfg = load_config(config_path)
        base_dir = cfg.get("_base_dir", ".")

    terminal_cfg = cfg.get("terminal", {}) if cfg else {}
    if cfg and not terminal_cfg:
        terminal_cfg = cfg

    _, term_dir, _ = resolve_terminal(terminal_cfg, base_dir=base_dir)
    exe_path = os.path.join(term_dir, "terminal64.exe")
    if not os.path.isfile(exe_path):
        raise FileNotFoundError(
            f"terminal64.exe not found in resolved terminal directory: {term_dir}"
        )
    return os.path.abspath(term_dir)


def install_portable_launcher(
    terminal_dir: Optional[str] = None,
    config_path: Optional[str] = None,
    overwrite: bool = False,
) -> str:
    """
    Writes `launch_mt5_portable.bat` (pure ASCII, CRLF) into the resolved
    portable MT5 directory and returns the absolute path to the created file.
    """
    term_dir = resolve_mt5_target_dir(terminal_dir=terminal_dir, config_path=config_path)
    target_path = os.path.abspath(os.path.join(term_dir, "launch_mt5_portable.bat"))

    if os.path.exists(target_path) and not overwrite:
        raise FileExistsError(f"Launcher already exists: {target_path}")

    with open(target_path, "w", encoding="ascii", newline="\r\n") as f:
        f.write(LAUNCH_MT5_PORTABLE_BAT)

    return target_path
