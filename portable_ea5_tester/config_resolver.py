"""
Configuration and Credential Resolver.

Handles resolution of terminal paths, EA/set file locations, and credentials
following a strict, deterministic resolution order. Zero silent fallbacks.
Standard library only.
"""

import os
import json
import shutil
from typing import Dict, Any, Optional, Tuple, List


import configparser


def load_json_file(file_path: str) -> Dict[str, Any]:
    """Loads a JSON file or raises ValueError if not found or invalid JSON."""
    if not file_path or not os.path.exists(file_path):
        raise ValueError(f"Configuration file not found: {file_path}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON syntax in '{file_path}': {e}") from e


def read_terminal_common_ini(terminal_dir: str) -> Dict[str, Any]:
    """
    Reads <terminal_dir>/Config/common.ini and extracts Login and Server from [Common].
    Supports utf-8, utf-16, latin-1 encodings.
    Returns dict like {"login": 12345678, "server": "MetaQuotes-Demo"} or empty dict.
    """
    if not terminal_dir:
        return {}

    common_ini_path = os.path.join(terminal_dir, "Config", "common.ini")
    if not os.path.isfile(common_ini_path):
        return {}

    content = None
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            with open(common_ini_path, "r", encoding=enc) as f:
                content = f.read()
                break
        except UnicodeDecodeError:
            continue
        except Exception:
            return {}

    if content is None:
        return {}

    parser = configparser.ConfigParser(strict=False)
    try:
        parser.read_string(content)
    except Exception:
        return {}

    if not parser.has_section("Common"):
        return {}

    res: Dict[str, Any] = {}
    if parser.has_option("Common", "Login"):
        raw_login = parser.get("Common", "Login").strip()
        if raw_login:
            res["login"] = int(raw_login) if raw_login.isdigit() else raw_login

    if parser.has_option("Common", "Server"):
        raw_server = parser.get("Common", "Server").strip()
        if raw_server:
            res["server"] = raw_server

    return res


def resolve_credentials(
    config: Optional[Dict[str, Any]] = None,
    base_dir: str = ".",
    terminal_dir: Optional[str] = None,
    is_offline: bool = False
) -> Dict[str, Any]:
    """
    Resolves account credentials in strict order:
    1. Credentials specified in config dictionary or via config['credentials_file']
    2. Auto-detection from MT5 terminal (<terminal_dir>/Config/common.ini)
    3. User home config (~/.config/portable-ea5-tester/credentials.json, fallback ~/.config/portable-strategy-tester/credentials.json)
    4. Environment variables (PEA5_LOGIN, PEA5_PASSWORD, PEA5_SERVER, fallback PST_LOGIN, PST_PASSWORD, PST_SERVER)

    If offline=True, returns empty or partial credentials without raising ValueError.
    If offline=False and login or server is missing, raises ValueError.
    """
    creds: Dict[str, Any] = {}
    config = config or {}

    # Step 1: Direct in config dictionary
    if "credentials" in config and isinstance(config["credentials"], dict):
        creds.update(config["credentials"])

    # Step 1b: Relative or absolute credentials_file in config
    creds_file = config.get("credentials_file")
    if creds_file and not creds.get("login"):
        file_path = creds_file if os.path.isabs(creds_file) else os.path.join(base_dir, creds_file)
        if os.path.exists(file_path):
            loaded = load_json_file(file_path)
            creds.update(loaded)

    # Step 1c: Check default ./credentials.json in base_dir
    if not creds.get("login"):
        default_file = os.path.join(base_dir, "credentials.json")
        if os.path.exists(default_file):
            loaded = load_json_file(default_file)
            creds.update(loaded)

    # Step 2: Auto-detect from MT5 terminal Config/common.ini if terminal_dir provided
    if (not creds.get("login") or not creds.get("server")) and terminal_dir:
        term_creds = read_terminal_common_ini(terminal_dir)
        if term_creds:
            if not creds.get("login") and term_creds.get("login"):
                creds["login"] = term_creds["login"]
            if not creds.get("server") and term_creds.get("server"):
                creds["server"] = term_creds["server"]
            print(f"[AUTH] Auto-detected active MT5 account from Config/common.ini: Login={creds.get('login')}, Server='{creds.get('server')}'")

    # Step 3: User home config
    if not creds.get("login") or not creds.get("server"):
        for cand_path in (
            "~/.config/portable-ea5-tester/credentials.json",
            "~/.config/portable-strategy-tester/credentials.json",
        ):
            user_home_file = os.path.expanduser(cand_path)
            if os.path.exists(user_home_file):
                try:
                    home_creds = load_json_file(user_home_file)
                    for k, v in home_creds.items():
                        if not creds.get(k):
                            creds[k] = v
                    break
                except Exception:
                    pass

    # Step 4: Environment variables
    env_login = os.environ.get("PEA5_LOGIN") or os.environ.get("PST_LOGIN")
    env_password = os.environ.get("PEA5_PASSWORD") or os.environ.get("PST_PASSWORD")
    env_server = os.environ.get("PEA5_SERVER") or os.environ.get("PST_SERVER")

    if not creds.get("login") and env_login:
        creds["login"] = int(env_login) if env_login.isdigit() else env_login
    if not creds.get("password") and env_password:
        creds["password"] = env_password
    if not creds.get("server") and env_server:
        creds["server"] = env_server

    # Zero silent fallback enforcement
    login = creds.get("login")
    server = creds.get("server")

    # Password is strictly optional (default to empty string if missing)
    if "password" not in creds or creds["password"] is None:
        creds["password"] = ""

    if not is_offline:
        if not login or not server:
            raise ValueError(
                "Missing account credentials: 'login' and 'server' are required when offline=False. "
                "Specify them in config.json ('credentials_file'), via environment variables "
                "(PEA5_LOGIN, PEA5_PASSWORD, PEA5_SERVER), or in ~/.config/portable-ea5-tester/credentials.json."
            )
    else:
        # In offline mode, if login or server is missing, return empty dict
        if not login or not server:
            return {}

    return creds


def resolve_terminal(
    terminal_cfg: Optional[Any] = None,
    base_dir: str = "."
) -> Tuple[str, str, Optional[str]]:
    """
    Resolves MT5 terminal executable, terminal root directory, and MetaEditor compiler.
    Gracefully supports BOTH structures:
    - Nested: config under "terminal" key (directory, executable, compiler)
    - Flat (legacy/web builder): top-level terminal_dir, terminal_exe, metaeditor_exe (or passed root config dict containing them)
    Returns: (terminal_exe_path, terminal_dir_path, compiler_exe_path)
    Raises FileNotFoundError if terminal executable cannot be located.
    """
    # Normalize terminal_cfg input
    if isinstance(terminal_cfg, dict):
        if "terminal" in terminal_cfg and isinstance(terminal_cfg["terminal"], dict):
            t_dict = terminal_cfg["terminal"]
        else:
            t_dict = terminal_cfg
    else:
        t_dict = {}

    raw_exe = t_dict.get("executable") or t_dict.get("terminal_exe")
    raw_dir = t_dict.get("directory") or t_dict.get("terminal_dir")
    raw_comp = t_dict.get("compiler") or t_dict.get("metaeditor_exe")

    term_exe: Optional[str] = None
    term_dir: Optional[str] = None
    comp_exe: Optional[str] = None

    if raw_exe:
        path = raw_exe if os.path.isabs(raw_exe) else os.path.join(base_dir, raw_exe)
        if os.path.exists(path) and os.path.isfile(path):
            term_exe = os.path.abspath(path)
            term_dir = os.path.dirname(term_exe)

    if not term_exe and raw_dir:
        dir_path = raw_dir if os.path.isabs(raw_dir) else os.path.join(base_dir, raw_dir)
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            term_dir = os.path.abspath(dir_path)
            for cand in ["terminal64.exe", "terminal.exe"]:
                p = os.path.join(term_dir, cand)
                if os.path.exists(p):
                    term_exe = p
                    break

    # Check local default directory candidate
    if not term_exe:
        default_dir = os.path.join(base_dir, "mt5_terminal")
        if os.path.exists(default_dir):
            for cand in ["terminal64.exe", "terminal.exe"]:
                p = os.path.join(default_dir, cand)
                if os.path.exists(p):
                    term_exe = os.path.abspath(p)
                    term_dir = os.path.abspath(default_dir)
                    break

    if not term_exe or not term_dir:
        raise FileNotFoundError(
            "MetaTrader 5 terminal executable not found. "
            "Please configure 'terminal.directory' or 'terminal.executable' in config.json."
        )

    # Resolve compiler
    if raw_comp:
        c_path = raw_comp if os.path.isabs(raw_comp) else os.path.join(base_dir, raw_comp)
        if os.path.exists(c_path):
            comp_exe = os.path.abspath(c_path)

    if not comp_exe and term_dir:
        for cand in ["metaeditor64.exe", "metaeditor.exe"]:
            c_path = os.path.join(term_dir, cand)
            if os.path.exists(c_path):
                comp_exe = c_path
                break

    return term_exe, term_dir, comp_exe


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Loads and normalizes config JSON.
    Supports single task configuration or multi-task structure ('common' + 'tasks').
    """
    raw = load_json_file(config_path)
    base_dir = os.path.dirname(os.path.abspath(config_path))
    raw["_base_dir"] = base_dir
    return raw
