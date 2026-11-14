"""
MQL5 Headless Compiler Wrapper.

Invokes MetaEditor (metaeditor64.exe) in headless mode to compile .mq5 source files.
Parses compilation log, counts errors/warnings, and verifies the generated .ex5 binary.
Standard library only. Pure ASCII output.
"""

import os
import sys
import re
import shutil
import subprocess
from typing import Dict, Any, Optional, List


def find_metaeditor(
    terminal_dir: Optional[str] = None,
    explicit_path: Optional[str] = None
) -> Optional[str]:
    """
    Locates metaeditor64.exe or metaeditor.exe.
    Priority:
    1. Explicit path parameter
    2. Within provided terminal_dir
    3. Standard Windows installation paths
    4. System PATH
    """
    if explicit_path and os.path.exists(explicit_path):
        return os.path.abspath(explicit_path)

    if terminal_dir and os.path.exists(terminal_dir):
        for name in ["metaeditor64.exe", "metaeditor.exe"]:
            candidate = os.path.join(terminal_dir, name)
            if os.path.exists(candidate):
                return os.path.abspath(candidate)

    standard_paths = [
        r"C:\Program Files\MetaTrader 5\metaeditor64.exe",
        r"C:\Program Files (x86)\MetaTrader 5\metaeditor64.exe",
        r"C:\Program Files\MetaTrader 5\metaeditor.exe",
    ]
    for p in standard_paths:
        if os.path.exists(p):
            return os.path.abspath(p)

    which_exe = shutil.which("metaeditor64.exe") or shutil.which("metaeditor.exe")
    if which_exe:
        return os.path.abspath(which_exe)

    return None


def parse_compiler_log(log_content: str) -> Dict[str, Any]:
    """
    Parses MT5 MetaEditor log content.
    Extracts total errors, warnings, and individual issue entries.
    """
    errors_list: List[Dict[str, Any]] = []
    warnings_list: List[Dict[str, Any]] = []
    errors_count = 0
    warnings_count = 0
    summary_found = False

    # Example line: C:\MQL5\Experts\MyEA.mq5(42,15) : error: undefined identifier
    line_pattern = re.compile(r"^(.*?)(?:\((\d+),(\d+)\))?\s*:\s*(\w+)\s*:\s*(.*)$")

    for line in log_content.splitlines():
        line = line.strip()
        if not line:
            continue

        # Check summary line: "Result: X errors, Y warnings"
        sum_match = re.search(r"Result:\s*(\d+)\s*errors,\s*(\d+)\s*warnings", line, re.IGNORECASE)
        if sum_match:
            errors_count = int(sum_match.group(1))
            warnings_count = int(sum_match.group(2))
            summary_found = True
            continue

        m = line_pattern.match(line)
        if m:
            f_path = m.group(1).strip()
            line_num = int(m.group(2)) if m.group(2) else 0
            col_num = int(m.group(3)) if m.group(3) else 0
            severity = m.group(4).lower()
            message = m.group(5).strip()

            if severity in ["information", "info"]:
                continue

            entry = {
                "file": os.path.basename(f_path),
                "full_path": f_path,
                "line": line_num,
                "column": col_num,
                "message": message,
            }

            if "error" in severity:
                errors_list.append(entry)
            elif "warning" in severity:
                warnings_list.append(entry)

    if not summary_found:
        errors_count = len(errors_list)
        warnings_count = len(warnings_list)

    return {
        "errors_count": errors_count,
        "warnings_count": warnings_count,
        "errors": errors_list,
        "warnings": warnings_list,
    }


def compile_ea(
    mq5_path: str,
    compiler_path: Optional[str] = None,
    terminal_dir: Optional[str] = None,
    include_dir: Optional[str] = None,
    timeout: int = 60
) -> Dict[str, Any]:
    """
    Compiles an .mq5 source file into .ex5 using MetaEditor.
    Returns structured results including error/warning lists and binary verification.
    """
    mq5_abs = os.path.abspath(mq5_path)
    if not os.path.exists(mq5_abs):
        raise FileNotFoundError(f"Target source file not found: {mq5_path}")

    compiler = find_metaeditor(terminal_dir=terminal_dir, explicit_path=compiler_path)
    if not compiler:
        raise FileNotFoundError(
            "MetaEditor compiler executable (metaeditor64.exe) not found. "
            "Please specify compiler path or terminal directory."
        )

    if not include_dir and terminal_dir:
        cand_inc = os.path.join(terminal_dir, "MQL5")
        if os.path.exists(cand_inc):
            include_dir = cand_inc

    base_dir = os.path.dirname(mq5_abs)
    stem, _ = os.path.splitext(os.path.basename(mq5_abs))
    log_path = os.path.join(base_dir, f"{stem}_compile.log")
    ex5_path = os.path.join(base_dir, f"{stem}.ex5")

    # Clean up stale log and note pre-compile ex5 mtime
    if os.path.exists(log_path):
        try:
            os.remove(log_path)
        except OSError:
            pass

    pre_mtime = os.path.getmtime(ex5_path) if os.path.exists(ex5_path) else 0.0

    cmd = [compiler, f"/compile:{mq5_abs}", f"/log:{log_path}"]
    if include_dir and os.path.exists(include_dir):
        cmd.append(f"/inc:{os.path.abspath(include_dir)}")

    print(f"[COMPILER] Compiling: {mq5_abs}")
    print(f"[COMPILER] Using: {compiler}")

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"MetaEditor timed out after {timeout} seconds compiling {mq5_abs}.")
    except Exception as e:
        raise RuntimeError(f"Failed to execute MetaEditor process: {e}")

    log_content = ""
    if os.path.exists(log_path):
        try:
            # MetaEditor logs are typically UTF-16LE with BOM
            with open(log_path, "r", encoding="utf-16le", errors="replace") as f:
                log_content = f.read()
                if log_content.startswith("\ufeff"):
                    log_content = log_content[1:]
        except Exception:
            try:
                with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                    log_content = f.read()
            except Exception:
                pass
        finally:
            try:
                os.remove(log_path)
            except OSError:
                pass

    parsed = parse_compiler_log(log_content)
    errors_cnt = parsed["errors_count"]
    warnings_cnt = parsed["warnings_count"]

    # Verify binary generation
    binary_created = False
    if os.path.exists(ex5_path):
        post_mtime = os.path.getmtime(ex5_path)
        if post_mtime >= pre_mtime:
            binary_created = True

    success = (errors_cnt == 0) and binary_created

    if success:
        print(f"[COMPILER] [PASS] Compilation succeeded ({warnings_cnt} warnings).")
        print(f"[COMPILER] Binary: {ex5_path}")
    else:
        print(f"[COMPILER] [FAIL] Compilation failed with {errors_cnt} errors and {warnings_cnt} warnings.")
        for err in parsed["errors"]:
            print(f"  Line {err['line']}: {err['message']}")

    return {
        "success": success,
        "mq5_path": mq5_abs,
        "ex5_path": ex5_path if binary_created else None,
        "errors_count": errors_cnt,
        "warnings_count": warnings_cnt,
        "errors": parsed["errors"],
        "warnings": parsed["warnings"],
        "log_text": log_content,
    }
