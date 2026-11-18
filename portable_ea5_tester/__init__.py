"""
portable-ea5-tester: Headless, portable MT5 EA (.mq5/.ex5) compilation and strategy testing framework.
Zero external runtime dependencies.
"""

__version__ = "1.0.0"

from .compiler import compile_ea
from .runner import run_tester
from .report_parser import parse_report
from .notebook_exporter import export_report
from .report_naming import resolve_report_destination

__all__ = [
    "compile_ea",
    "run_tester",
    "parse_report",
    "export_report",
    "resolve_report_destination",
]
