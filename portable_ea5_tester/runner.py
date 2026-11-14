"""
MT5 Strategy Tester Execution Engine.

Generates temporary UTF-16LE configuration INI files with sensitive credentials,
invokes terminal64.exe in portable mode, monitors process health with timeouts,
relocates artifacts, and guarantees temporary credential cleanup in a finally block.
Standard library only. Pure ASCII output.
"""

import os
import sys
import glob
import time
import shutil
import subprocess
import re
import json
import builtins
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(line_buffering=True, write_through=True)
        except Exception:
            pass

_builtin_print = builtins.print


def print(*args, **kwargs):
    kwargs.setdefault("flush", True)
    _builtin_print(*args, **kwargs)
    try:
        sys.stdout.flush()
    except Exception:
        pass

from .lock import TesterLock
from .config_resolver import resolve_credentials, resolve_terminal, load_config
from .report_parser import parse_report, format_summary_table, parse_optimization_xml, generate_optimization_html
from .compiler import compile_ea, find_metaeditor
from .report_naming import resolve_report_destination


def diagnose_tester_failure(
    term_dir: str,
    current_symbol: Optional[str] = None,
    start_time: Optional[float] = None
) -> List[str]:
    """
    Scans MT5 Strategy Tester logs for common failure patterns:
    - Authorization / synchronization errors with trade server
    - Missing historical data
    - Missing or invalid symbol errors scoped to current_symbol if provided
    Returns list of diagnostic advice strings. Pure ASCII.
    """
    advice: List[str] = []
    log_candidates: List[str] = []

    # Common log directories in MT5 portable mode
    potential_log_dirs = [
        os.path.join(term_dir, "Tester", "logs"),
        os.path.join(term_dir, "MQL5", "Logs"),
        os.path.join(term_dir, "logs"),
        term_dir,
    ]

    for ld in potential_log_dirs:
        if os.path.exists(ld):
            files = glob.glob(os.path.join(ld, "*.log"))
            if start_time is not None:
                files = [f for f in files if os.path.getmtime(f) >= (start_time - 5.0)]
            files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            log_candidates.extend(files)

    content_agg = ""
    # Process up to 5 most recent log files
    cutoff_time_str = None
    if start_time is not None:
        # Convert start_time (minus 2.0s for clock drift) to local HH:MM:SS
        dt_start = datetime.fromtimestamp(start_time - 2.0)
        cutoff_time_str = dt_start.strftime("%H:%M:%S")

    time_regex = re.compile(r"(?:^|\s|\t)(\d{2}:\d{2}:\d{2})(?:\.\d+)?")

    for log_file in log_candidates[:5]:
        try:
            with open(log_file, "rb") as bf:
                raw_bytes = bf.read()
            text = ""
            if raw_bytes.startswith(b"\xff\xfe") or raw_bytes.startswith(b"\xfe\xff"):
                text = raw_bytes.decode("utf-16", errors="replace")
            elif raw_bytes.startswith(b"\xef\xbb\xbf"):
                text = raw_bytes.decode("utf-8-sig", errors="replace")
            else:
                for enc in ["utf-8", "utf-16-le", "latin-1"]:
                    try:
                        text = raw_bytes.decode(enc)
                        break
                    except UnicodeDecodeError:
                        continue

            if cutoff_time_str is not None:
                filtered_lines = []
                for line in text.splitlines():
                    m_time = time_regex.search(line)
                    if m_time:
                        line_time_str = m_time.group(1)
                        if line_time_str >= cutoff_time_str:
                            filtered_lines.append(line)
                    else:
                        filtered_lines.append(line)
                text = "\n".join(filtered_lines)

            content_agg += "\n" + text
        except Exception:
            continue

    content_lower = content_agg.lower()

    if "not synchronized with trade server" in content_lower or "tester agent authorization error" in content_lower or "authorization failed" in content_lower:
        advice.append(
            "[AGENT SYNC ERROR] Tester agent is not synchronized with the trade server!\n"
            "  Action: Launch MT5 GUI once to log into your account, download symbols, or ensure historical data cache is initialized."
        )

    if "tester not started because the account is not specified" in content_lower or "account is not specified" in content_lower:
        advice.append(
            "[ACCOUNT SETUP REQUIRED] MT5 has not cached login credentials for this account/server.\n"
            "  Action: Run 'login.bat' once, enter your password, check 'Save password', and click OK."
        )

    if "no history data" in content_lower or "history data not found" in content_lower or "cannot load history" in content_lower:
        advice.append(
            "[MISSING HISTORY DATA] No historical data found for the selected symbol/timeframe!\n"
            "  Action: Open MT5 chart for this symbol/timeframe once to download and build cache."
        )

    if current_symbol:
        escaped_sym = re.escape(current_symbol)
        matched_curr = re.search(rf"symbol\s+{escaped_sym}\s+not exist", content_agg, re.IGNORECASE)
        cannot_select_curr = ("cannot select symbol in market watch" in content_lower or "cannot select symbol" in content_lower) and (current_symbol.lower() in content_lower)

        if matched_curr or cannot_select_curr:
            advice.append(
                f"[INVALID SYMBOL ERROR] Symbol '{current_symbol}' does not exist on your broker server!\n"
                f"  Action: Check your broker's exact symbol naming convention (e.g. '{current_symbol}.FX', '{current_symbol}m', etc.) in Market Watch."
            )
        elif "tester symbol does not exist" in content_lower:
            advice.append(
                f"[INVALID SYMBOL ERROR] Symbol '{current_symbol}' does not exist on your broker server!\n"
                f"  Action: Check Market Watch in MT5 GUI for the exact symbol name used by your broker."
            )
    else:
        sym_matches = re.findall(r"symbol\s+([A-Za-z0-9_.]+)\s+not exist", content_agg, re.IGNORECASE)
        stop_words = {"does", "name", "the", "a", "is"}
        filtered_syms = [s for s in sym_matches if s.lower() not in stop_words]

        if filtered_syms:
            last_sym = filtered_syms[-1]
            advice.append(
                f"[INVALID SYMBOL ERROR] Symbol '{last_sym}' does not exist on your broker server!\n"
                f"  Action: Check your broker's exact symbol naming convention (e.g. '{last_sym}.FX', '{last_sym}m', etc.) in Market Watch."
            )
        elif "tester symbol does not exist" in content_lower:
            advice.append(
                "[INVALID SYMBOL ERROR] Specified symbol does not exist on your broker server!\n"
                f"  Action: Check Market Watch in MT5 GUI for the exact symbol name used by your broker."
            )
        elif "cannot select symbol in market watch" in content_lower or "cannot select symbol" in content_lower or "symbol not exist" in content_lower:
            advice.append(
                "[INVALID SYMBOL ERROR] Cannot select symbol in Market Watch!\n"
                "  Action: The specified symbol may not exist or is not enabled for trading on this broker account."
            )

    return advice



def normalize_date(date_str: str) -> str:
    """Normalizes various date formats to MT5 Tester format 'YYYY.MM.DD'."""
    if not date_str:
        return ""
    date_str = str(date_str).strip()
    formats = ["%Y.%m.%d", "%m/%d/%Y", "%Y-%m-%d", "%Y/%m/%d"]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y.%m.%d")
        except ValueError:
            continue
    raise ValueError(f"Invalid date format: '{date_str}'. Expected 'YYYY.MM.DD' or 'YYYY-MM-DD'.")


def create_tester_ini(
    ini_path: str,
    account: Optional[Dict[str, Any]],
    tester: Dict[str, Any],
    report_filename: str
) -> None:
    """
    Creates MT5 configuration INI file as UTF-16LE with BOM.
    Contains [Common] and [Tester] sections.
    """
    lines: List[str] = ["[Common]"]

    if account:
        login = account.get("login")
        server = account.get("server")
        password = account.get("password")
        if login:
            lines.append(f"Login={login}")
        if server:
            lines.append(f"Server={server}")
        if password and str(password).strip():
            lines.append(f"Password={password}")

    lines.extend([
        "ProxyEnable=0",
        "CertConfirm=0",
        "NewsEnable=0",
        "Sound=0",
        "",
        "[Tester]",
        f"Expert={tester.get('expert')}",
        f"Symbol={tester.get('symbol')}",
        f"Period={tester.get('period')}",
        f"Model={tester.get('model', 0)}",
        f"Optimization={int(tester.get('optimization', 0))}",
        f"OptimizationCriterion={int(tester.get('optimization_criterion', 0))}" if int(tester.get("optimization", 0)) > 0 else None,
    ])
    lines = [l for l in lines if l is not None]

    shutdown_terminal = tester.get("shutdown_terminal", True)
    lines.extend([
        f"ExecutionMode={tester.get('execution_mode', 0)}",
        f"FromDate={tester.get('from_date')}",
        f"ToDate={tester.get('to_date')}",
        f"Deposit={tester.get('deposit', 10000)}",
        f"Currency={tester.get('currency', 'USD')}",
        f"Leverage={tester.get('leverage', 50)}",
        "UseLocal=1",
        "ReplaceReport=1",
        "Visual=0",
        f"ShutdownTerminal={1 if shutdown_terminal else 0}",
        f"Report={report_filename}",
    ])

    set_file = tester.get("set_file")
    if set_file:
        lines.append(f"ExpertParameters={set_file}")
        lines.append(f"Parameters={set_file}")

    lines.append("")

    with open(ini_path, "w", encoding="utf-16-le", newline="\r\n") as f:
        f.write("\ufeff" + "\n".join(lines) + "\n")


def copy_expert_to_terminal(expert_path: str, terminal_dir: str) -> str:
    """
    Ensures EA .ex5 exists and is copied into terminal_dir/MQL5/Experts/.
    - Strips `.mq5` extension if present to get base name.
    - Looks for `.ex5` candidate.
    - If `.ex5` does not exist and `.mq5` exists, compiles `.mq5` via `compiler.compile_ea(...)`.
    - Returns base name / relative filename without `.mq5` suitable for INI Expert= setting.
    """
    experts_dir = os.path.join(terminal_dir, "MQL5", "Experts")
    os.makedirs(experts_dir, exist_ok=True)

    # Strip .mq5 extension if present
    base_name = expert_path
    if base_name.endswith(".mq5"):
        base_name = base_name[:-4]

    # Candidates for source .ex5 or source .mq5
    candidates = [
        expert_path,
        base_name + ".ex5",
        os.path.join(terminal_dir, expert_path),
        os.path.join(terminal_dir, base_name + ".ex5"),
        os.path.join(experts_dir, os.path.basename(expert_path)),
        os.path.join(experts_dir, os.path.basename(base_name) + ".ex5"),
    ]

    found_ex5: Optional[str] = None
    for cand in candidates:
        if cand.endswith(".ex5") and os.path.exists(cand) and os.path.isfile(cand):
            found_ex5 = os.path.abspath(cand)
            break

    if not found_ex5:
        # Look for .mq5 source to compile
        mq5_candidates = [
            expert_path if expert_path.endswith(".mq5") else expert_path + ".mq5",
            base_name + ".mq5",
            os.path.join(terminal_dir, expert_path if expert_path.endswith(".mq5") else expert_path + ".mq5"),
            os.path.join(terminal_dir, base_name + ".mq5"),
            os.path.join(experts_dir, os.path.basename(expert_path) if expert_path.endswith(".mq5") else os.path.basename(expert_path) + ".mq5"),
            os.path.join(experts_dir, os.path.basename(base_name) + ".mq5"),
        ]
        found_mq5: Optional[str] = None
        for mcand in mq5_candidates:
            if os.path.exists(mcand) and os.path.isfile(mcand):
                found_mq5 = os.path.abspath(mcand)
                break

        if found_mq5:
            print(f"[SYNC] Found .mq5 source: {found_mq5}. Compiling into .ex5...")
            comp_res = compile_ea(mq5_path=found_mq5, terminal_dir=terminal_dir)
            if comp_res["success"] and comp_res.get("ex5_path"):
                found_ex5 = comp_res["ex5_path"]
            else:
                raise RuntimeError(f"Failed to compile EA source: {found_mq5} (Errors: {comp_res.get('errors_count', 0)})")

    if not found_ex5:
        raise FileNotFoundError(f"Expert Advisor file (.ex5 or .mq5) not found: {expert_path}")

    dest_filename = os.path.basename(found_ex5)
    dest_path = os.path.join(experts_dir, dest_filename)

    if os.path.abspath(found_ex5) != os.path.abspath(dest_path):
        shutil.copy2(found_ex5, dest_path)
        print(f"[SYNC] Copied EA binary: {found_ex5} -> {dest_path}")

    # Return base name without extension or with .ex5 (MT5 accepts both)
    # Here we strip .ex5 so INI has Expert=Sample_MA_Cross or return dest_filename
    # To be fully safe and clean: return os.path.splitext(dest_filename)[0]
    return os.path.splitext(dest_filename)[0]


def copy_set_file_to_terminal(set_path: Optional[str], terminal_dir: str) -> Optional[str]:
    """
    Copies preset .set file to terminal_dir/MQL5/Profiles/Tester/.
    Returns basename for INI parameter.
    """
    if not set_path:
        return None

    tester_profiles = os.path.join(terminal_dir, "MQL5", "Profiles", "Tester")
    os.makedirs(tester_profiles, exist_ok=True)

    candidates = [
        set_path,
        os.path.join(terminal_dir, set_path),
        os.path.join(tester_profiles, os.path.basename(set_path)),
    ]
    if not set_path.endswith(".set"):
        candidates.extend([c + ".set" for c in list(candidates)])

    found_src: Optional[str] = None
    for cand in candidates:
        if os.path.exists(cand) and os.path.isfile(cand):
            found_src = os.path.abspath(cand)
            break

    if not found_src:
        raise FileNotFoundError(f"Preset set file not found: {set_path}")

    dest_filename = os.path.basename(found_src)
    dest_path = os.path.join(tester_profiles, dest_filename)

    if os.path.abspath(found_src) != os.path.abspath(dest_path):
        shutil.copy2(found_src, dest_path)
        print(f"[SYNC] Copied preset: {found_src} -> {dest_path}")

    return dest_filename


def run_process_monitor(
    cmd: List[str],
    cwd: str,
    timeout: int = 600,
    poll_interval: float = 1.0,
    heartbeat_interval: float = 10.0
) -> float:
    """Executes tester process with periodic heartbeat and timeout monitor."""
    print(f"[LAUNCH] Executing: {' '.join(cmd)}")
    start_time = time.time()
    last_heartbeat = start_time

    proc = subprocess.Popen(cmd, cwd=cwd)

    try:
        while proc.poll() is None:
            time.sleep(poll_interval)
            now = time.time()
            elapsed = now - start_time

            if heartbeat_interval > 0 and (now - last_heartbeat >= heartbeat_interval):
                print(f"[MONITOR] MT5 Strategy Tester running... (elapsed: {int(elapsed)}s)")
                last_heartbeat = now

            if elapsed >= timeout:
                print(f"[ERROR] Strategy Tester timed out after {timeout}s. Terminating...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                raise TimeoutError(f"Strategy Tester process exceeded timeout of {timeout}s.")
    except Exception:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        raise

    elapsed_total = time.time() - start_time
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd)

    return elapsed_total


def relocate_report_artifacts(
    report_filename: str,
    terminal_dir: str,
    target_dir: str
) -> str:
    """Locates generated report in terminal directory and moves it to target directory."""
    os.makedirs(target_dir, exist_ok=True)
    # Strip common report extensions to get clean stem
    clean_stem = report_filename
    for ext in [".html", ".xml", ".htm", ".csv"]:
        if clean_stem.lower().endswith(ext):
            clean_stem = clean_stem[:-len(ext)]
            break

    _, req_ext = os.path.splitext(report_filename)
    if not req_ext:
        req_ext = ".html"

    # Candidates in priority order
    candidate_names = [
        report_filename,
        f"{clean_stem}{req_ext}",
        f"{clean_stem}.xml",
        f"{clean_stem}.html",
        f"{clean_stem}.html.xml",
        f"{clean_stem}.htm",
    ]
    # Unique candidates while preserving order
    unique_names = []
    for n in candidate_names:
        if n not in unique_names:
            unique_names.append(n)

    candidates = []
    for cname in unique_names:
        candidates.append(os.path.join(terminal_dir, cname))
        candidates.append(os.path.join(terminal_dir, "Reports", cname))

    found_src: Optional[str] = None
    for cand in candidates:
        if os.path.exists(cand) and os.path.isfile(cand):
            found_src = os.path.abspath(cand)
            # Determine appropriate final extension
            # If the source file is .xml or .html.xml, final target should be .xml
            # If the source file is .html or .htm, final target should be .html
            cand_lower = cand.lower()
            if cand_lower.endswith(".xml"):
                target_path = os.path.join(target_dir, f"{clean_stem}.xml")
            elif cand_lower.endswith(".html") or cand_lower.endswith(".htm"):
                target_path = os.path.join(target_dir, f"{clean_stem}.html")
            else:
                _, actual_ext = os.path.splitext(cand)
                target_path = os.path.join(target_dir, f"{clean_stem}{actual_ext}")
            break

    if not found_src:
        raise FileNotFoundError(
            f"Generated test report not found ({report_filename}). "
            f"Searched: {candidates}"
        )

    if os.path.abspath(found_src) != os.path.abspath(target_path):
        shutil.copy2(found_src, target_path)
        try:
            os.remove(found_src)
        except OSError:
            pass

    # Move accompanying charts (.png)
    base_stem, _ = os.path.splitext(report_filename)
    search_dirs = [os.path.dirname(found_src), terminal_dir, os.path.join(terminal_dir, "Reports")]
    for sdir in set(search_dirs):
        if not os.path.exists(sdir):
            continue
        for png in glob.glob(os.path.join(sdir, f"{base_stem}*.png")):
            dest_png = os.path.join(target_dir, os.path.basename(png))
            if os.path.abspath(png) != os.path.abspath(dest_png):
                shutil.copy2(png, dest_png)
                try:
                    os.remove(png)
                except OSError:
                    pass

    return os.path.normpath(target_path)


def run_tester(
    config: Optional[Dict[str, Any]] = None,
    config_path: Optional[str] = None,
    task_index: Optional[int] = None,
    offline_override: Optional[bool] = None,
    timeout_override: Optional[int] = None
) -> Dict[str, Any]:
    """
    Main orchestrator for MT5 Strategy Tester execution.
    1. Resolves terminal and credentials.
    2. Copies EA and set files to portable folder.
    3. Acquires inter-process tester.lock.
    4. Generates temporary UTF-16LE INI with BOM.
    5. Spawns terminal64.exe /portable /config:<ini>.
    6. Ensures INI cleanup in finally block.
    7. Relocates and parses reports.
    """
    if config_path and not config:
        config = load_config(config_path)
    config = config or {}
    base_dir = config.get("_base_dir", ".")

    # Extract tasks
    tasks: List[Dict[str, Any]] = []
    common_cfg = config.get("common", {})
    if "tasks" in config and isinstance(config["tasks"], list) and len(config["tasks"]) > 0:
        for t in config["tasks"]:
            merged = dict(common_cfg)
            merged.update(t)
            tasks.append(merged)
    else:
        # Single task configuration
        tasks = [config]

    if task_index is not None:
        if task_index < 0 or task_index >= len(tasks):
            raise IndexError(f"Task index {task_index} out of range (0-{len(tasks)-1}).")
        tasks = [tasks[task_index]]

    # Terminal resolution
    terminal_cfg = config.get("terminal", {})
    term_exe, term_dir, _ = resolve_terminal(terminal_cfg, base_dir=base_dir)

    all_results: List[Dict[str, Any]] = []

    for idx, task in enumerate(tasks):
        is_offline = bool(task.get("offline", False))
        if offline_override is not None:
            is_offline = offline_override

        timeout = int(task.get("timeout", 600))
        if timeout_override is not None:
            timeout = timeout_override

        hb_val = task.get("heartbeat_interval", common_cfg.get("heartbeat_interval", 10.0))
        try:
            heartbeat_interval = float(hb_val)
        except (ValueError, TypeError):
            heartbeat_interval = 10.0

        # Resolve credentials
        creds = resolve_credentials(config, base_dir=base_dir, terminal_dir=term_dir, is_offline=is_offline)

        # Pre-launch guard for MT5 account identification
        if not creds.get("login") or not creds.get("server"):
            print(
                "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
                "[ERROR] Missing MT5 Account Information (Login / Server)!\n"
                "  Even in OFFLINE mode, MT5 Strategy Tester requires 'login' and 'server'\n"
                "  to locate broker history in 'bases/<ServerName>/' and symbol specifications.\n\n"
                "  Password is NOT required for offline testing (can be omitted or left blank).\n\n"
                "  Action: Create or specify 'credentials.json' containing:\n"
                "          {\"login\": 12345678, \"server\": \"MetaQuotes-Demo\"}\n"
                "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            )
            raise RuntimeError("Missing required MT5 account identification ('login' and 'server').")

        # EA and Set resolution
        ea_rel = copy_expert_to_terminal(task["expert"], term_dir)
        set_rel = copy_set_file_to_terminal(task.get("set_file"), term_dir)

        # Report destination & naming resolution
        task_with_context = dict(task)
        if len(tasks) > 1 and not task.get("report_name"):
            target_report_dir, report_name = resolve_report_destination(task_with_context, base_dir=base_dir)
            stem, ext = os.path.splitext(report_name)
            report_name = f"{stem}_t{idx+1}{ext}"
        else:
            target_report_dir, report_name = resolve_report_destination(task_with_context, base_dir=base_dir)

        # Lock acquisition
        lock_file = os.path.join(term_dir, "tester.lock")
        lock = TesterLock(lock_file, timeout=float(timeout))

        symbol = task.get("symbol", "N/A")
        period = task.get("period", "N/A")
        from_d = task.get("from_date", "")
        to_d = task.get("to_date", "")
        print(f"\n[{idx+1}/{len(tasks)}] Testing {symbol} {period} ({from_d} -> {to_d})...")

        ini_path = os.path.join(term_dir, "temp_tester.ini")
        start_exec_time = time.time()

        try:
            with lock:
                try:
                    tester_params = {
                        "expert": ea_rel,
                        "symbol": task["symbol"],
                        "period": task["period"],
                        "model": task.get("model", 0),
                        "optimization": task.get("optimization", 0),
                        "optimization_criterion": task.get("optimization_criterion", 0),
                        "execution_mode": task.get("execution_mode", 0),
                        "from_date": normalize_date(task["from_date"]),
                        "to_date": normalize_date(task["to_date"]),
                        "deposit": task.get("deposit", 10000),
                        "currency": task.get("currency", 'USD'),
                        "leverage": task.get("leverage", 50),
                        "set_file": set_rel,
                        "shutdown_terminal": task.get("shutdown_terminal", True),
                    }

                    create_tester_ini(ini_path, creds, tester_params, report_name)

                    cmd = [term_exe, "/portable", f"/config:{ini_path}"]
                    elapsed = run_process_monitor(
                        cmd,
                        cwd=term_dir,
                        timeout=timeout,
                        heartbeat_interval=heartbeat_interval
                    )
                    print(f"[RUNNER] Process execution completed in {elapsed:.1f}s.")

                finally:
                    # Guaranteed cleanup of sensitive temporary INI
                    if os.path.exists(ini_path):
                        try:
                            os.remove(ini_path)
                        except OSError:
                            pass

            # Relocate report
            final_report_path = relocate_report_artifacts(report_name, term_dir, target_report_dir)

            # Freshness verification
            report_mtime = os.path.getmtime(final_report_path)
            if report_mtime < start_exec_time - 2.0:
                raise RuntimeError(
                    f"Freshness check failed: Report '{final_report_path}' was not updated during this test run."
                )

    
            is_opt = int(task.get("optimization", 0)) > 0
            parsed = {}
            if is_opt:
                try:
                    parsed = parse_optimization_xml(final_report_path)
                except Exception as ex:
                    print(f"  [INFO] Optimization report saved at '{final_report_path}' (fallback XML/HTML parser: {ex})")
                    try:
                        parsed = parse_report(final_report_path)
                    except Exception:
                        parsed = {
                            "metadata": {"expert": task.get("expert"), "symbol": task.get("symbol")},
                            "metrics": {},
                            "trades": [],
                            "passes": [],
                            "passes_count": 0,
                            "optimization": True
                        }
            else:
                parsed = parse_report(final_report_path)

            metrics = parsed.get("metrics", {})
            net_prof = metrics.get("total_net_profit")
            trades_count = metrics.get("total_trades", len(parsed.get("trades", [])))
            pf = metrics.get("profit_factor")
            curr = parsed.get("metadata", {}).get("currency", "USD")

            if not is_opt:
                net_prof_str = f"{net_prof:+.2f} {curr}" if net_prof is not None else "N/A"
                pf_str = f"{pf:.2f}" if pf is not None else "N/A"

                print(f"  [COMPLETED] Net Profit: {net_prof_str} | Trades: {trades_count} | PF: {pf_str}")

                # Low History Quality check
                common_cfg = config.get("common", {}) if isinstance(config, dict) else {}
                min_quality = float(task.get("min_history_quality", common_cfg.get("min_history_quality", 90.0)))
                hq_val = metrics.get("history_quality")
                if hq_val is not None and hq_val < min_quality:
                    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    print("[WARN] [LOW DATA QUALITY WARNING]")
                    print(f"  History Quality: {hq_val:.1f}% (Below threshold: {min_quality}%)")
                    print("  The broker lacks low-timeframe data for this test period!")
                    print("  MT5 has fallen back to coarse or daily bars. Results may suffer from")
                    print("  severe slippage, execution, or lookahead biases.")
                    print("  Action: Shorten the backtest date range or download M1 data in MT5.")
                    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

                # Diagnosis check if 0 trades
                if trades_count == 0:
                    print(f"[WARN] Test produced 0 trades.")
                    advices = diagnose_tester_failure(term_dir, current_symbol=symbol, start_time=start_exec_time)
                    for adv in advices:
                        print(f"[DIAGNOSIS] {adv}")
            else:
                passes_cnt = parsed.get("passes_count", 0)
                print(f"  [COMPLETED] Optimization run finished ({passes_cnt} passes). Report saved to: {final_report_path}")
            html_report_path = None
            if is_opt and final_report_path.lower().endswith(".xml"):
                try:
                    html_report_path = os.path.splitext(final_report_path)[0] + ".html"
                    generate_optimization_html(final_report_path, html_report_path)
                    print(f"  [HTML] Generated Optimization Dashboard: {html_report_path}")
                except Exception as ex:
                    print(f"  [WARN] Failed to generate HTML optimization dashboard: {ex}")

            # Output formats options
            common_cfg = config.get("common", {}) if isinstance(config, dict) else {}
            out_formats = common_cfg.get("output_formats", {}) if isinstance(common_cfg, dict) else {}
            fmt_html = bool(out_formats.get("html", True))
            fmt_json = bool(out_formats.get("json", True))
            keep_charts = bool(out_formats.get("keep_charts", True))

            # Chart images cleanup if keep_charts is False or HTML is disabled
            if not keep_charts or not fmt_html:
                rep_dir = os.path.dirname(final_report_path)
                rep_stem, _ = os.path.splitext(os.path.basename(final_report_path))
                if os.path.exists(rep_dir):
                    for png in glob.glob(os.path.join(rep_dir, f"{rep_stem}*.png")):
                        try:
                            os.remove(png)
                        except OSError:
                            pass

            # AI-Friendly JSON report (<ReportName>.json)
            json_report_path = None
            if fmt_json:
                try:
                    rep_stem, _ = os.path.splitext(final_report_path)
                    json_report_path = f"{rep_stem}.json"
                    json_payload = {
                        "metadata": parsed.get("metadata", {}),
                        "metrics": parsed.get("metrics", {}),
                        "trades": parsed.get("trades", []),
                        "passes": parsed.get("passes", []),
                        "best_pass": parsed.get("best_pass"),
                        "task": {
                            "symbol": task.get("symbol"),
                            "period": task.get("period"),
                            "expert": task.get("expert"),
                            "set_file": task.get("set_file"),
                            "from_date": task.get("from_date"),
                            "to_date": task.get("to_date"),
                            "deposit": task.get("deposit"),
                            "currency": task.get("currency"),
                            "leverage": task.get("leverage"),
                            "optimization": task.get("optimization", 0),
                        }
                    }
                    with open(json_report_path, "w", encoding="utf-8") as jf:
                        json.dump(json_payload, jf, indent=2, ensure_ascii=False)
                    print(f"  [AI-JSON] Generated JSON Report: {json_report_path}")
                except Exception as ex:
                    print(f"  [WARN] Failed to generate AI JSON report: {ex}")

            all_results.append({
                "task": task,
                "report_path": final_report_path,
                "html_report_path": html_report_path or final_report_path,
                "json_report_path": json_report_path,
                "parsed": parsed,
            })

        except Exception as e:
            print(f"  [FAILED] Task #{idx+1} failed: {e}")
            advices = diagnose_tester_failure(term_dir, current_symbol=symbol, start_time=start_exec_time)
            for adv in advices:
                print(f"[DIAGNOSIS] {adv}")
            raise

    # Batch summary JSON output
    common_cfg = config.get("common", {}) if isinstance(config, dict) else {}
    out_formats = common_cfg.get("output_formats", {}) if isinstance(common_cfg, dict) else {}
    fmt_batch_json = bool(out_formats.get("batch_summary_json", True))
    if fmt_batch_json and all_results:
        try:
            first_rep = all_results[0]["report_path"]
            batch_dir = os.path.dirname(first_rep)
            batch_json_path = os.path.join(batch_dir, "batch_summary.json")

            batch_tasks_summary = []
            total_net_pnl = 0.0
            total_trades_all = 0

            for r_item in all_results:
                t_info = r_item.get("task", {})
                m_info = r_item.get("parsed", {}).get("metrics", {})
                meta_info = r_item.get("parsed", {}).get("metadata", {})
                tr_list = r_item.get("parsed", {}).get("trades", [])
                p_list = r_item.get("parsed", {}).get("passes", [])
                bp = r_item.get("parsed", {}).get("best_pass")

                pnl = m_info.get("total_net_profit")
                if pnl is None and bp and bp.get("Profit") is not None:
                    pnl = bp.get("Profit")
                if pnl is not None:
                    total_net_pnl += pnl

                t_cnt = m_info.get("total_trades", len(tr_list))
                if t_cnt == 0 and bp and bp.get("Trades") is not None:
                    t_cnt = int(bp.get("Trades"))
                total_trades_all += t_cnt

                batch_tasks_summary.append({
                    "symbol": t_info.get("symbol") or meta_info.get("symbol"),
                    "period": t_info.get("period") or meta_info.get("period"),
                    "expert": t_info.get("expert") or meta_info.get("expert"),
                    "set_file": t_info.get("set_file"),
                    "optimization": t_info.get("optimization", 0),
                    "report_path": r_item.get("report_path"),
                    "json_report_path": r_item.get("json_report_path"),
                    "metrics": m_info,
                    "best_pass": bp,
                    "passes_count": len(p_list),
                    "trades_count": t_cnt,
                })

            batch_summary_data = {
                "generated_at": datetime.now().isoformat(),
                "total_tasks": len(all_results),
                "cumulative_net_profit": round(total_net_pnl, 2),
                "total_trades": total_trades_all,
                "tasks": batch_tasks_summary,
            }
            with open(batch_json_path, "w", encoding="utf-8") as bjf:
                json.dump(batch_summary_data, bjf, indent=2, ensure_ascii=False)
            print(f"[SUMMARY] Generated Batch Summary JSON: {batch_json_path}")
        except Exception as ex:
            print(f"[WARN] Failed to generate batch summary JSON: {ex}")

    return {
        "tasks_count": len(all_results),
        "results": all_results,
    }
