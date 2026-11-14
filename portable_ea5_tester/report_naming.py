"""
Automated Report Naming & Subfolder Organization for MT5 Strategy Tester.
Supports dynamic placeholders, subfolder structuring, invalid character sanitization,
and auto-incrementing to prevent overwriting existing reports.
Standard library only. Pure ASCII.
"""

import os
import re
from datetime import datetime
from typing import Dict, Any, Optional, Tuple


INVALID_CHARS_REGEX = re.compile(r'[\\/:*?"<>|]')


def sanitize_filename_component(name: str, replacement: str = "_") -> str:
    """
    Sanitizes string to be safe for Windows file and folder names.
    Replaces invalid characters (\\ / : * ? " < > |) with replacement string.
    Trims leading/trailing whitespace and periods.
    """
    if not name:
        return ""
    sanitized = INVALID_CHARS_REGEX.sub(replacement, str(name))
    # Avoid reserved characters and excessive periods/spaces
    sanitized = sanitized.strip(" .")
    return sanitized or replacement


def format_placeholder(
    template: str,
    task: Dict[str, Any],
    now: Optional[datetime] = None
) -> str:
    """
    Expands supported placeholders in the template string:
    - {datetime}: YYYYMMDD_HHMMSS
    - {date}: YYYYMMDD
    - {time}: HHMMSS
    - {ea}: Base filename of expert (sanitized)
    - {symbol}: Symbol (e.g. USDJPY)
    - {period}: Timeframe (e.g. H1)
    - {set}: Base filename of set_file, or 'default' if not specified
    - {type}: 'opt' if optimization > 0 else 'test'
    """
    if now is None:
        now = datetime.now()

    ea_raw = task.get("expert", "")
    ea_name = os.path.splitext(os.path.basename(ea_raw))[0] if ea_raw else "EA"
    ea_clean = sanitize_filename_component(ea_name)

    symbol = sanitize_filename_component(task.get("symbol", "TEST"))
    period = sanitize_filename_component(task.get("period", "H1"))

    set_raw = task.get("set_file", "")
    if set_raw:
        set_name = os.path.splitext(os.path.basename(set_raw))[0]
    else:
        set_name = "default"
    set_clean = sanitize_filename_component(set_name)

    is_opt = int(task.get("optimization", 0)) > 0
    type_str = "opt" if is_opt else "test"

    replacements = {
        "{datetime}": now.strftime("%Y%m%d_%H%M%S"),
        "{date}": now.strftime("%Y%m%d"),
        "{time}": now.strftime("%H%M%S"),
        "{ea}": ea_clean,
        "{symbol}": symbol,
        "{period}": period,
        "{set}": set_clean,
        "{type}": type_str,
    }

    result = template
    for key, val in replacements.items():
        result = result.replace(key, val)

    return result


def resolve_report_destination(
    task: Dict[str, Any],
    base_dir: str = ".",
    now: Optional[datetime] = None
) -> Tuple[str, str]:
    """
    Determines final target report directory and report filename (with appropriate extension).

    Returns:
        (target_report_dir, report_filename_with_ext)

    Features:
    - Preserves exact compatibility when task has fixed report_name or report_dir.
    - Expands dynamic placeholders in report_name or default naming pattern.
    - Handles use_subfolder (using folder_template or default '{date}_{ea}').
    - Handles folder auto-increment (if subfolder already exists, appends _01, _02 to avoid collision).
    - Handles auto_increment for report files (appends _01, _02 if target report file already exists).
    - Windows path normalization and sanitization.
    """
    if now is None:
        now = datetime.now()

    is_opt = int(task.get("optimization", 0)) > 0
    target_ext = ".xml" if is_opt else ".html"

    # Base report directory
    raw_report_dir = task.get("report_dir") or "reports"
    clean_report_dir = raw_report_dir.strip().replace("/", "\\")
    if clean_report_dir.startswith("\\") and not clean_report_dir.startswith("\\\\"):
        clean_report_dir = clean_report_dir.lstrip("\\")

    if not os.path.isabs(clean_report_dir):
        resolved_report_dir = os.path.abspath(os.path.join(base_dir, clean_report_dir))
    else:
        resolved_report_dir = os.path.abspath(clean_report_dir)
    resolved_report_dir = os.path.normpath(resolved_report_dir)

    # Subfolder handling
    use_subfolder = bool(task.get("use_subfolder", False))
    auto_increment_subfolder = bool(task.get("subfolder_auto_increment", task.get("auto_increment", False)))

    if use_subfolder:
        folder_template = task.get("folder_template") or "{date}_{ea}"
        expanded_folder = format_placeholder(folder_template, task, now=now)
        # Sanitize folder path components (allow sub-path separators if intended, but sanitize parts)
        parts = re.split(r"[\\/]+", expanded_folder)
        clean_parts = [sanitize_filename_component(p) for p in parts if p.strip()]
        if clean_parts:
            # If auto-incrementing subfolder, we check if target directory exists on disk
            # For multi-level paths (e.g. sym/period_date), increment the last folder component
            candidate_parts = list(clean_parts)
            candidate_dir = os.path.normpath(os.path.join(resolved_report_dir, *candidate_parts))

            if auto_increment_subfolder and os.path.exists(candidate_dir):
                last_comp = candidate_parts[-1]
                counter = 1
                while os.path.exists(candidate_dir):
                    candidate_parts[-1] = f"{last_comp}_{counter:02d}"
                    candidate_dir = os.path.normpath(os.path.join(resolved_report_dir, *candidate_parts))
                    counter += 1

            resolved_report_dir = candidate_dir

    # Filename resolution
    user_report_name = task.get("report_name")
    if user_report_name and user_report_name.strip():
        expanded_name = format_placeholder(user_report_name.strip(), task, now=now)
        # Strip extension if supplied to append target_ext accurately
        stem = expanded_name
        for ext in [".html", ".xml", ".htm", ".csv"]:
            if stem.lower().endswith(ext):
                stem = stem[:-len(ext)]
                break
        clean_stem = sanitize_filename_component(stem)
        report_name = f"{clean_stem}{target_ext}"
    else:
        # Default report name
        set_stem = ""
        if task.get("set_file"):
            set_clean = sanitize_filename_component(os.path.splitext(os.path.basename(task["set_file"]))[0])
            set_stem = f"_{set_clean}"
        opt_flag = "_opt" if is_opt else ""
        sym = sanitize_filename_component(task.get("symbol", "TEST"))
        per = sanitize_filename_component(task.get("period", "H1"))
        stem = f"Report_{sym}_{per}{set_stem}{opt_flag}"
        report_name = f"{stem}{target_ext}"

    # Auto-increment handling
    auto_increment = bool(task.get("auto_increment", False))
    if auto_increment:
        base_stem, ext = os.path.splitext(report_name)
        candidate_path = os.path.join(resolved_report_dir, report_name)
        counter = 1
        while os.path.exists(candidate_path):
            report_name = f"{base_stem}_{counter:02d}{ext}"
            candidate_path = os.path.join(resolved_report_dir, report_name)
            counter += 1

    return (resolved_report_dir, report_name)
