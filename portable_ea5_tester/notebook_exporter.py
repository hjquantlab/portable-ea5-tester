"""
Markdown & NotebookLM Report Exporter.

Converts parsed MT5 reports into pure Markdown, compact CSV trade logs,
and structured JSON metrics optimized for Jupyter Notebooks, Google NotebookLM,
and automated LLM analysis.
Clean, neutral output. Standard library only.
"""

import os
import json
from typing import Dict, Any, List, Optional
from .report_parser import parse_report, export_trades_csv


def generate_markdown_content(report_dict: Dict[str, Any]) -> str:
    """Generates structured, clean Markdown content from parsed report dictionary."""
    meta = report_dict.get("metadata", {})
    metrics = report_dict.get("metrics", {})
    trades = report_dict.get("trades", [])

    lines: List[str] = []
    lines.append(f"# Strategy Tester Report: {meta.get('expert', 'Strategy')}")
    lines.append("")
    lines.append("## 1. Test Configuration")
    lines.append("")
    lines.append(f"- **Symbol**: {meta.get('symbol', 'N/A')}")
    lines.append(f"- **Timeframe / Period**: {meta.get('period', 'N/A')}")
    lines.append(f"- **Currency**: {meta.get('currency', 'USD')}")
    lines.append(f"- **Initial Deposit**: {meta.get('initial_deposit', 'N/A')}")
    lines.append(f"- **Leverage**: {meta.get('leverage', 'N/A')}")
    lines.append("")

    inputs = meta.get("inputs", {})
    lines.append("### Input Parameters")
    lines.append("")
    if inputs:
        lines.append("| Parameter | Value |")
        lines.append("| :--- | :--- |")
        for k, v in inputs.items():
            lines.append(f"| {k} | {v} |")
    else:
        lines.append("_No custom inputs extracted._")
    lines.append("")

    lines.append("## 2. Key Performance Indicators")
    lines.append("")
    lines.append("| Metric | Value | Description |")
    lines.append("| :--- | :--- | :--- |")

    def _fmt(val, digits=2, suffix=""):
        if val is None:
            return "N/A"
        if isinstance(val, (int, float)):
            return f"{val:.{digits}f}{suffix}"
        return f"{val}{suffix}"

    lines.append(f"| Total Net Profit | {_fmt(metrics.get('total_net_profit'))} | Net balance gain/loss |")
    lines.append(f"| Gross Profit | {_fmt(metrics.get('gross_profit'))} | Cumulative profits |")
    lines.append(f"| Gross Loss | {_fmt(metrics.get('gross_loss'))} | Cumulative losses |")
    lines.append(f"| Profit Factor | {_fmt(metrics.get('profit_factor'))} | Gross profit / Gross loss |")
    lines.append(f"| Expected Payoff | {_fmt(metrics.get('expected_payoff'))} | Expected payoff per trade |")
    lines.append(f"| Sharpe Ratio | {_fmt(metrics.get('sharpe_ratio'))} | Risk-adjusted return |")
    lines.append(f"| Recovery Factor | {_fmt(metrics.get('recovery_factor'))} | Net profit / Max drawdown |")
    lines.append(f"| Total Trades | {metrics.get('total_trades', 0)} | Completed closed trades |")
    lines.append(f"| Total Deals | {metrics.get('total_deals', 0)} | Order fills (in + out) |")
    lines.append(f"| Margin Level | {_fmt(metrics.get('margin_level'), 2, '%')} | Minimum margin level |")

    bal_dd = metrics.get("balance_drawdown_maximal", {})
    eq_dd = metrics.get("equity_drawdown_maximal", {})
    lines.append(f"| Balance DD Maximal | {_fmt(bal_dd.get('money'))} ({_fmt(bal_dd.get('pct'), 2, '%')}) | Balance drawdown |")
    lines.append(f"| Equity DD Maximal | {_fmt(eq_dd.get('money'))} ({_fmt(eq_dd.get('pct'), 2, '%')}) | Equity drawdown |")
    lines.append("")

    # Trade distributions
    win_trades = [t for t in trades if t.get("pnl", 0) > 0]
    loss_trades = [t for t in trades if t.get("pnl", 0) < 0]
    win_rate = (len(win_trades) / len(trades) * 100.0) if trades else 0.0

    lines.append("## 3. Trade Distribution")
    lines.append("")
    lines.append(f"- **Total Closed Trades**: {len(trades)}")
    lines.append(f"- **Profitable Trades**: {len(win_trades)} ({win_rate:.1f}%)")
    lines.append(f"- **Losing Trades**: {len(loss_trades)} ({100.0 - win_rate:.1f}%)")
    lines.append("")

    # Best & Worst trades
    sorted_trades = sorted(trades, key=lambda x: x.get("pnl", 0.0), reverse=True)
    best_trades = sorted_trades[:10]
    worst_trades = sorted_trades[-10:][::-1] if trades else []

    lines.append("## 4. Top 10 Best Trades")
    lines.append("")
    if best_trades:
        lines.append("| ID | Entry Time | Exit Time | Type | Lot | Entry Px | Exit Px | PnL | Pips |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for t in best_trades:
            lines.append(
                f"| {t.get('id')} | {t.get('t_in')} | {t.get('t_out')} | {t.get('type')} | "
                f"{t.get('lot')} | {t.get('p_in')} | {t.get('p_out')} | {t.get('pnl')} | {t.get('pips')} |"
            )
    else:
        lines.append("_No trades recorded._")
    lines.append("")

    lines.append("## 5. Top 10 Worst Trades")
    lines.append("")
    if worst_trades:
        lines.append("| ID | Entry Time | Exit Time | Type | Lot | Entry Px | Exit Px | PnL | Pips |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for t in worst_trades:
            lines.append(
                f"| {t.get('id')} | {t.get('t_in')} | {t.get('t_out')} | {t.get('type')} | "
                f"{t.get('lot')} | {t.get('p_in')} | {t.get('p_out')} | {t.get('pnl')} | {t.get('pips')} |"
            )
    else:
        lines.append("_No trades recorded._")
    lines.append("")

    lines.append("---")
    lines.append("_Generated by portable-ea5-tester_")
    lines.append("")

    return "\n".join(lines)


def export_report(
    report_path: str,
    output_dir: str,
    export_csv: bool = True,
    export_json: bool = True
) -> Dict[str, str]:
    """
    Parses an MT5 Strategy Tester report and exports clean artifacts:
    - *_report.md (Markdown report)
    - *_trades.csv (Reconstructed compact trades)
    - *_metrics.json (Structured KPIs)
    Returns dictionary of generated file paths.
    """
    report_dict = parse_report(report_path)
    os.makedirs(output_dir, exist_ok=True)

    stem = os.path.splitext(os.path.basename(report_path))[0]
    results: Dict[str, str] = {}

    # 1. Markdown
    md_content = generate_markdown_content(report_dict)
    md_path = os.path.join(output_dir, f"{stem}_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    results["markdown"] = md_path

    # 2. CSV
    if export_csv:
        csv_path = os.path.join(output_dir, f"{stem}_trades.csv")
        export_trades_csv(report_dict.get("trades", []), csv_path)
        results["trades_csv"] = csv_path

    # 3. JSON
    if export_json:
        json_path = os.path.join(output_dir, f"{stem}_metrics.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        results["metrics_json"] = json_path

    return results
