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


def _decode_log_bytes(raw_bytes: bytes) -> str:
    """
    Decodes raw MetaEditor log bytes (UTF-16LE with/without BOM, UTF-8, or latin-1).
    """
    if not raw_bytes:
        return ""

    if raw_bytes.startswith(b"\xff\xfe") or b"\x00" in raw_bytes:
        text = raw_bytes.decode("utf-16-le", errors="replace")
        if text.startswith("\ufeff"):
            text = text[1:]
        return text

    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = raw_bytes.decode("latin-1", errors="replace")

    if text.startswith("\ufeff"):
        text = text[1:]
    return text


def parse_compiler_log(
    log_content: str,
    target_filename: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Parses MT5 MetaEditor log content (both /log: output and logs/metaeditor.log).
    Extracts total errors, warnings, and individual issue entries.
    When target_filename is provided and multiple summary lines exist, prefers
    summary lines matching target_filename (case-insensitive).
    """
    errors_list: List[Dict[str, Any]] = []
    warnings_list: List[Dict[str, Any]] = []
    errors_count = 0
    warnings_count = 0
    summary_found = False
    last_summary: Optional[tuple] = None
    target_summary: Optional[tuple] = None
    target_lower = target_filename.lower() if target_filename else None

    # Example line: C:\MQL5\Experts\MyEA.mq5(42,15) : error: undefined identifier
    line_pattern = re.compile(r"^(.*?)(?:\((\d+),(\d+)\))?\s*:\s*(\w+)\s*:\s*(.*)$")
    # Summary patterns:
    # - "Result: X errors, Y warnings"
    # - "0\t12:34:56\tCompile\tMyEA.mq5 - 0 errors, 0 warnings"
    # - "X errors, Y warnings"
    result_summary_pattern = re.compile(
        r"Result:\s*(\d+)\s*errors?,\s*(\d+)\s*warnings?",
        re.IGNORECASE,
    )
    metaeditor_summary_pattern = re.compile(
        r"(?:^|[\s\t\-:])(\d+)\s+errors?,\s*(\d+)\s+warnings?(?:\b|$)",
        re.IGNORECASE,
    )

    for line in log_content.splitlines():
        line = line.strip()
        if not line:
            continue

        sum_match = result_summary_pattern.search(line) or metaeditor_summary_pattern.search(line)
        if sum_match:
            pair = (int(sum_match.group(1)), int(sum_match.group(2)))
            last_summary = pair
            summary_found = True
            if target_lower and target_lower in line.lower():
                target_summary = pair
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

    if summary_found:
        chosen = target_summary if target_summary is not None else last_summary
        if chosen is not None:
            errors_count, warnings_count = chosen
    else:
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
    timeout: int = 60,
    log_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compiles an .mq5 source file into .ex5 using MetaEditor.
    By default (log_path=None), omits /log: to avoid MetaEditor path/space quirks
    and reads newly appended entries from <terminal_dir>/logs/metaeditor.log.
    If log_path is explicitly provided, passes /log:<log_path> and reads that file.
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
    ex5_path = os.path.join(base_dir, f"{stem}.ex5")
    pre_mtime = os.path.getmtime(ex5_path) if os.path.exists(ex5_path) else 0.0

    explicit_log_abs: Optional[str] = None
    metaeditor_log: Optional[str] = None
    pre_log_size = 0

    cmd = [compiler, f"/compile:{mq5_abs}"]

    if log_path is not None:
        explicit_log_abs = os.path.abspath(log_path)
        log_parent = os.path.dirname(explicit_log_abs)
        if log_parent:
            os.makedirs(log_parent, exist_ok=True)
        if os.path.exists(explicit_log_abs):
            try:
                os.remove(explicit_log_abs)
            except OSError:
                pass
        cmd.append(f"/log:{explicit_log_abs}")
    else:
        effective_terminal_dir = terminal_dir or os.path.dirname(compiler)
        metaeditor_log = os.path.join(effective_terminal_dir, "logs", "metaeditor.log")
        if os.path.exists(metaeditor_log):
            try:
                pre_log_size = os.path.getsize(metaeditor_log)
            except OSError:
                pre_log_size = 0

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
    if explicit_log_abs is not None:
        if os.path.exists(explicit_log_abs):
            try:
                with open(explicit_log_abs, "rb") as f:
                    log_content = _decode_log_bytes(f.read())
            except Exception:
                pass
    elif metaeditor_log and os.path.exists(metaeditor_log):
        try:
            current_size = os.path.getsize(metaeditor_log)
            start_offset = 0 if current_size < pre_log_size else pre_log_size
            with open(metaeditor_log, "rb") as f:
                if start_offset > 0:
                    f.seek(start_offset)
                log_content = _decode_log_bytes(f.read())
        except Exception:
            pass

    parsed = parse_compiler_log(log_content, target_filename=os.path.basename(mq5_abs))
    errors_cnt = parsed["errors_count"]
    warnings_cnt = parsed["warnings_count"]

    # Verify binary generation
    binary_created = False
    if os.path.exists(ex5_path):
        post_mtime = os.path.getmtime(ex5_path)
        if pre_mtime == 0.0 or post_mtime > pre_mtime:
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
