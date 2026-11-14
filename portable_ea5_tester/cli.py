"""
Command-Line Interface for portable-ea5-tester (pea5).

Provides subcommands:
- run: Execute strategy tester backtest tasks.
- compile: Headless MQL5 compilation with MetaEditor.
- init: Diagnostic environment verification wizard.

Standard library only. Pure ASCII output.
"""

import os
import sys
import argparse
import builtins
from typing import Optional

import webbrowser

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

try:
    from .compiler import compile_ea, find_metaeditor
    from .runner import run_tester
    from .config_resolver import resolve_terminal, resolve_credentials, load_config
    from .notebook_exporter import export_report
    from .report_parser import generate_batch_summary_html
    # Open-Core design: gui.py is an optional Pro / standalone binary-edition module
    # intentionally excluded from the open-source CLI repository (not a missing file).
    try:
        from .gui import launch_gui
    except ImportError:
        launch_gui = None
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from portable_ea5_tester.compiler import compile_ea, find_metaeditor
    from portable_ea5_tester.runner import run_tester
    from portable_ea5_tester.config_resolver import resolve_terminal, resolve_credentials, load_config
    from portable_ea5_tester.notebook_exporter import export_report
    from portable_ea5_tester.report_parser import generate_batch_summary_html
    # Open-Core design: gui.py is an optional Pro / standalone binary-edition module
    # intentionally excluded from the open-source CLI repository (not a missing file).
    try:
        from portable_ea5_tester.gui import launch_gui
    except ImportError:
        launch_gui = None

TRADEMARK_DISCLAIMER = (
    "DISCLAIMER: MetaTrader, MT5, and MQL5 are registered trademarks of MetaQuotes Ltd.\n"
    "portable-ea5-tester (pea5) is an independent open-source tool and is NOT affiliated with, endorsed by, "
    "or sponsored by MetaQuotes Ltd."
)


def cmd_run(args: argparse.Namespace) -> int:
    """Executes backtests based on configuration JSON."""
    config_file = args.config
    if not os.path.exists(config_file):
        print(f"[ERROR] Configuration file not found: {config_file}")
        return 1

    try:
        results = run_tester(
            config_path=config_file,
            task_index=args.task,
            offline_override=args.offline,
            timeout_override=args.timeout,
        )
        print(f"[SUCCESS] All {results['tasks_count']} backtest tasks executed successfully.")

        if args.export:
            for item in results["results"]:
                rep_path = os.path.normpath(item["report_path"])
                out_dir = os.path.dirname(rep_path)
                exported = export_report(rep_path, out_dir)
                exp_md = os.path.normpath(exported.get('markdown')) if exported.get('markdown') else None
                print(f"[EXPORT] Exported Markdown report: {exp_md}")

        # Generate Batch Summary HTML Dashboard
        summary_html_path = None
        if results.get("results"):
            first_rep = os.path.normpath(results["results"][0]["report_path"])
            rep_dir = os.path.dirname(first_rep)
            summary_html_path = os.path.normpath(os.path.join(rep_dir, "batch_summary.html"))
            generate_batch_summary_html(results["results"], summary_html_path)
            print(f"[SUMMARY] Generated Batch Summary Dashboard: {os.path.normpath(summary_html_path)}")

        # Auto-open dashboard if requested
        if getattr(args, "open_report", True):
            target_open = summary_html_path
            if not target_open and results.get("results"):
                target_open = os.path.normpath(results["results"][0]["report_path"])

            if target_open and os.path.exists(target_open):
                print(f"[BROWSER] Opening dashboard: {os.path.normpath(target_open)}")
                webbrowser.open(f"file://{os.path.abspath(target_open)}")

        return 0
    except Exception as e:
        print(f"[FATAL] Test execution failed: {e}")
        return 1



def cmd_compile(args: argparse.Namespace) -> int:
    """Compiles an MQL5 file (.mq5) into .ex5."""
    mq5_file = args.file
    if not os.path.exists(mq5_file):
        print(f"[ERROR] Source file not found: {mq5_file}")
        return 1

    try:
        res = compile_ea(
            mq5_path=mq5_file,
            compiler_path=args.compiler,
            terminal_dir=args.terminal_dir,
            include_dir=args.include,
            timeout=args.timeout or 60,
        )
        return 0 if res["success"] else 1
    except Exception as e:
        print(f"[FATAL] Compilation error: {e}")
        return 1


def cmd_init(args: argparse.Namespace) -> int:
    """Diagnostic wizard to check paths and credentials."""
    print("=" * 70)
    print(" portable-ea5-tester (pea5): Environment Diagnostic Wizard")
    print("=" * 70)

    # 1. Config check
    cfg_path = args.config or "config.json"
    cfg = None
    if os.path.exists(cfg_path):
        print(f"[CHECK] Config file found: {cfg_path} -> [PASS]")
        try:
            cfg = load_config(cfg_path)
        except Exception as e:
            print(f"[WARN] Failed to parse config JSON: {e}")
    else:
        print(f"[CHECK] Config file: '{cfg_path}' not found -> [WARN] (Create from config.example.json)")

    # 2. Terminal executable check
    term_dir = None
    if cfg:
        try:
            term_exe, term_dir, comp_exe = resolve_terminal(cfg.get("terminal", {}), base_dir=cfg.get("_base_dir", "."))
            print(f"[CHECK] Terminal executable: {term_exe} -> [PASS]")
            if comp_exe:
                print(f"[CHECK] MetaEditor compiler: {comp_exe} -> [PASS]")
            else:
                print("[CHECK] MetaEditor compiler: not detected in terminal dir -> [WARN]")
        except Exception as e:
            print(f"[CHECK] Terminal detection: {e} -> [FAIL]")
    else:
        # Check standard default candidate
        def_term = os.path.abspath("./mt5_terminal")
        print(f"[CHECK] Default terminal directory ({def_term}): {'[EXISTS]' if os.path.exists(def_term) else '[NOT FOUND]'}")

    # 3. Compiler check
    compiler = find_metaeditor(terminal_dir=term_dir)
    if compiler:
        print(f"[CHECK] Global compiler detection: {compiler} -> [PASS]")
    else:
        print("[CHECK] Global compiler detection: Not found in standard paths -> [WARN]")

    # 4. Credentials check
    try:
        creds = resolve_credentials(cfg, is_offline=True)
        if creds.get("login") and creds.get("server"):
            print(f"[CHECK] Account credentials: Login={creds.get('login')}, Server={creds.get('server')} -> [PASS]")
        else:
            print("[CHECK] Account credentials: Missing login or server (offline testing only) -> [INFO]")
    except Exception as e:
        print(f"[CHECK] Account credentials check: {e} -> [WARN]")

    print("=" * 70)
    print("Diagnostic complete.")
    return 0


def cmd_login(args: argparse.Namespace) -> int:
    """
    Launch MT5 GUI in interactive mode for account login and credential caching.
    Pre-fills Login and Server in startup config so MT5 opens login dialog directly.
    """
    import subprocess
    import tempfile

    config_file = args.config
    cfg = None
    if os.path.exists(config_file):
        try:
            cfg = load_config(config_file)
        except Exception as e:
            print(f"[WARN] Failed to load config file '{config_file}': {e}")
    else:
        print(f"[INFO] Config file '{config_file}' not found. Using default discovery.")

    try:
        term_exe, term_dir, _ = resolve_terminal(cfg.get("terminal", {}) if cfg else {}, base_dir=cfg.get("_base_dir", ".") if cfg else ".")
    except Exception as e:
        print(f"[ERROR] Failed to resolve MT5 terminal: {e}")
        return 1

    login = None
    server = None
    if cfg:
        try:
            creds = resolve_credentials(cfg, is_offline=True)
            login = creds.get("login")
            server = creds.get("server")
        except Exception:
            pass

    tmp_ini = None
    cmd = [term_exe, "/portable"]

    if login and server:
        tmp_fd, tmp_ini = tempfile.mkstemp(prefix="pst_login_", suffix=".ini", dir=term_dir)
        os.close(tmp_fd)
        lines = [
            "[Common]",
            f"Login={login}",
            f"Server={server}",
            ""
        ]
        with open(tmp_ini, "w", encoding="utf-16-le", newline="\r\n") as f:
            f.write("\ufeff" + "\n".join(lines) + "\n")
        cmd.append(f"/config:{os.path.basename(tmp_ini)}")

    print("=" * 70)
    print("  [MT5 Interactive Login Setup]")
    print("  Opening MT5 GUI.")
    if login and server:
        print(f"  Target Account: Login={login}, Server={server}")
    print("  If prompted, enter your password in the Login dialog, check \"Save password\", and click OK.")
    print("  Once logged in, close MT5 to complete this setup and return to the terminal.")
    print("=" * 70)

    try:
        proc = subprocess.Popen(cmd, cwd=term_dir)
        proc.wait()
        print("[INFO] MT5 GUI session ended.")
        return 0
    except Exception as e:
        print(f"[ERROR] Failed to launch MT5 GUI: {e}")
        return 1
    finally:
        if tmp_ini and os.path.exists(tmp_ini):
            try:
                os.remove(tmp_ini)
            except Exception:
                pass


def main(argv: Optional[list] = None) -> None:
    """Main CLI entry point."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(line_buffering=True, write_through=True)
            except Exception:
                pass

    parser = argparse.ArgumentParser(
        prog="pea5",
        description=f"portable-ea5-tester (pea5): Headless MT5 EA compilation & Strategy Tester automation.\n\n{TRADEMARK_DISCLAIMER}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Subcommand to execute")

    # Subcommand: run
    p_run = subparsers.add_parser("run", help="Execute backtest tasks from configuration file")
    p_run.add_argument("--config", "-c", type=str, default="config.json", help="Path to config.json (default: config.json)")
    p_run.add_argument("--task", "-t", type=int, default=None, help="Zero-based index of specific task to run")
    p_run.add_argument("--offline", action="store_true", default=None, help="Force offline testing without broker login")
    p_run.add_argument("--timeout", type=int, default=None, help="Process timeout override in seconds")
    p_run.add_argument("--export", "-e", action="store_true", default=False, help="Export Markdown and compact CSV reports")
    p_run.add_argument("--open-report", dest="open_report", action="store_true", default=True, help="Automatically open report dashboard in browser (default: True)")
    p_run.add_argument("--no-open-report", dest="open_report", action="store_false", help="Disable automatic opening of dashboard in browser")

    # Subcommand: login
    p_login = subparsers.add_parser("login", help="Launch MT5 GUI in interactive mode for account login and credential caching")
    p_login.add_argument("--config", default="tester_config.json", help="Path to config file")

    # Subcommand: compile
    p_comp = subparsers.add_parser("compile", help="Compile MQL5 EA (.mq5) into .ex5")
    p_comp.add_argument("--file", "-f", type=str, required=True, help="Path to .mq5 source file")
    p_comp.add_argument("--compiler", type=str, default=None, help="Path to metaeditor64.exe")
    p_comp.add_argument("--terminal-dir", type=str, default=None, help="Portable MT5 directory containing compiler")
    p_comp.add_argument("--include", "-i", type=str, default=None, help="Additional include directory (/inc:)")
    p_comp.add_argument("--timeout", type=int, default=60, help="Compilation timeout in seconds (default: 60)")

    # Subcommand: init
    p_init = subparsers.add_parser("init", help="Run diagnostic environment wizard")
    p_init.add_argument("--config", "-c", type=str, default="config.json", help="Path to config.json to check")

    # Subcommand: menu
    p_menu = subparsers.add_parser("menu", help="Launch standalone Tkinter GUI control center")
    p_menu.add_argument("--config", "-c", type=str, default="tester_config.json", help="Path to config.json (default: tester_config.json)")

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "run":
        sys.exit(cmd_run(args))
    elif args.command == "login":
        sys.exit(cmd_login(args))
    elif args.command == "compile":
        sys.exit(cmd_compile(args))
    elif args.command == "init":
        sys.exit(cmd_init(args))
    elif args.command == "menu":
        # Open-Core design: gui.py is an optional Pro / standalone binary-edition module
        # intentionally excluded from the open-source CLI repository (not a missing file).
        if launch_gui is None:
            print("[ERROR] GUI module is not available in the standalone CLI core edition.")
            sys.exit(1)
            return
        sys.exit(launch_gui(args.config))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
