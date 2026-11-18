"""
MT5 Strategy Tester Report Parser.

Standard library parser for MetaTrader 5 Strategy Tester HTML reports.
Extracts high-level KPIs, trade statistics, drawdowns, and reconstructs
executed trade logs into structured dictionaries and CSV files.
Clean neutral output. Pure ASCII logs.
"""

import os
import re
import csv
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, List, Tuple


def _read_report_content(file_path: str) -> Optional[str]:
    """Reads HTML report file trying common encodings (UTF-16, UTF-16LE, UTF-8-sig, UTF-8, latin-1)."""
    encodings = ["utf-16", "utf-16-le", "utf-8-sig", "utf-8", "latin-1"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                content = f.read()
                if "Strategy Tester" in content or "Total Net Profit" in content or "<html" in content.lower():
                    return content
        except Exception:
            continue
    try:
        with open(file_path, "r", errors="ignore") as f:
            return f.read()
    except Exception:
        return None


def _clean_number(val_str: Optional[str]) -> Optional[float]:
    """Extracts floating point number from string representation."""
    if val_str is None:
        return None
    cleaned = (
        str(val_str)
        .replace("&nbsp;", "")
        .replace("&#160;", "")
        .replace(" ", "")
        .replace(",", "")
        .replace("%", "")
        .strip()
    )
    m = re.search(r"[-+]?\d*\.?\d+", cleaned)
    if m:
        try:
            return float(m.group(0))
        except ValueError:
            return None
    return None


def _extract_metric_cell(content: str, label: str) -> Optional[str]:
    """Finds cell content following a given label in HTML table rows."""
    pattern = rf"{re.escape(label)}:?</td>\s*<td[^>]*>(?:<b[^>]*>)?(.*?)(?:</b>)?</td>"
    m = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
    if m:
        val = re.sub(r"<[^>]+>", "", m.group(1))
        return val.replace("&nbsp;", " ").replace("&#160;", " ").strip()
    return None


def _parse_dd_pair(content: str, label: str) -> Tuple[Optional[float], Optional[float]]:
    """Extracts money and percentage drawdown values from a cell."""
    raw = _extract_metric_cell(content, label)
    if not raw:
        return None, None
    m1 = re.search(r"([\d\.\s,]+)\s*\(([\d\.\s]+)%\)", raw)
    if m1:
        return _clean_number(m1.group(1)), _clean_number(m1.group(2))
    m2 = re.search(r"([\d\.\s]+)%\s*\(([\d\.\s,]+)\)", raw)
    if m2:
        return _clean_number(m2.group(2)), _clean_number(m2.group(1))
    return _clean_number(raw), None


def parse_metadata(content: str) -> Dict[str, Any]:
    """Extracts test environment, symbol, period, deposit, and EA inputs."""
    meta: Dict[str, Any] = {
        "title": "Strategy Tester Report",
        "expert": "",
        "symbol": "",
        "period": "",
        "currency": "",
        "initial_deposit": None,
        "leverage": "",
        "inputs": {},
    }

    m_title = re.search(r"<title>(.*?)</title>", content, re.IGNORECASE)
    if m_title:
        meta["title"] = m_title.group(1).strip()

    meta["expert"] = _extract_metric_cell(content, "Expert") or ""
    meta["symbol"] = _extract_metric_cell(content, "Symbol") or ""
    meta["period"] = _extract_metric_cell(content, "Period") or ""
    meta["currency"] = _extract_metric_cell(content, "Currency") or ""
    raw_dep = _extract_metric_cell(content, "Initial Deposit")
    meta["initial_deposit"] = _clean_number(raw_dep) if raw_dep else None
    meta["leverage"] = _extract_metric_cell(content, "Leverage") or ""

    # Inputs chunk extraction
    inp_pos = content.find("Inputs:")
    if inp_pos != -1:
        end_pos = content.find("Company:", inp_pos)
        chunk = content[inp_pos:end_pos] if end_pos != -1 else content[inp_pos:inp_pos + 4000]
        items = re.findall(r"<b>\s*([^<]+=[^<]+)\s*</b>", chunk)
        inputs_dict = {}
        for item in items:
            parts = item.split("=", 1)
            k = parts[0].strip()
            v = parts[1].strip()
            if k and not k.startswith("==="):
                inputs_dict[k] = v
        meta["inputs"] = inputs_dict

    return meta


def parse_trades_and_orders(content: str, symbol_hint: str = "") -> List[Dict[str, Any]]:
    """
    Parses Orders and Deals tables and reconstructs completed closed trades.
    Reconstructed trade fields: id, t_in, type, lot, p_in, sl, tp, t_out, p_out, pnl, pips.
    """
    orders: Dict[str, Dict[str, Any]] = {}
    orders_idx = content.find("<b>Orders</b>")
    deals_idx = content.find("<b>Deals</b>")

    if orders_idx != -1 and deals_idx != -1 and orders_idx < deals_idx:
        orders_part = content[orders_idx:deals_idx]
        orders_rows = re.findall(r"<tr[^>]*align=right[^>]*>(.*?)</tr>", orders_part, re.DOTALL)
        for r in orders_rows:
            cols = [re.sub(r"<[^>]+>", "", x).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", r, re.DOTALL)]
            if len(cols) >= 11:
                # Open Time, Order, Symbol, Type, Volume, Price, S/L, T/P, Time, State, Comment
                order_id = cols[1]
                orders[order_id] = {
                    "open_time": cols[0],
                    "symbol": cols[2],
                    "type": cols[3].lower(),
                    "volume": cols[4],
                    "price": cols[5],
                    "sl": cols[6],
                    "tp": cols[7],
                }

    trades: List[Dict[str, Any]] = []
    if deals_idx != -1:
        deals_part = content[deals_idx:]
        deals_rows = re.findall(r"<tr[^>]*align=right[^>]*>(.*?)</tr>", deals_part, re.DOTALL)
        deals = []
        for r in deals_rows:
            cols = [re.sub(r"<[^>]+>", "", x).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", r, re.DOTALL)]
            if len(cols) >= 13 and cols[3].lower() in ["buy", "sell"]:
                deals.append(cols)

        current_in = None
        for d in deals:
            t_deal, deal_id, sym, d_type, direction, vol, price, order_id, comm, swap, profit, bal, cmt = d[:13]
            d_type = d_type.lower()
            direction = direction.lower()

            if direction == "in":
                current_in = d
            elif direction == "out" and current_in:
                in_time = current_in[0]
                in_sym = current_in[2]
                in_type = current_in[3].lower()
                in_vol = current_in[5]
                in_price = current_in[6]
                in_order_id = current_in[7]

                order_info = orders.get(in_order_id, {})
                sl_str = order_info.get("sl", "")
                tp_str = order_info.get("tp", "")

                try:
                    p_in = float(in_price)
                    p_out = float(price)
                    lot = float(in_vol)
                    pnl_clean = str(profit).replace(" ", "").replace("&nbsp;", "").replace(",", "")
                    pnl = float(pnl_clean)
                except ValueError:
                    continue

                symbol_name = sym or in_sym or symbol_hint
                mult = 100.0 if "JPY" in symbol_name.upper() else 10000.0
                if in_type == "buy":
                    pips = (p_out - p_in) * mult
                else:
                    pips = (p_in - p_out) * mult

                sl_val = round(float(sl_str), 5) if sl_str and sl_str != "0.00000" else ""
                tp_val = round(float(tp_str), 5) if tp_str and tp_str != "0.00000" else ""

                trades.append({
                    "id": len(trades) + 1,
                    "t_in": in_time,
                    "type": in_type,
                    "lot": round(lot, 2),
                    "p_in": round(p_in, 5),
                    "sl": sl_val,
                    "tp": tp_val,
                    "t_out": t_deal,
                    "p_out": round(p_out, 5),
                    "pnl": round(pnl, 2),
                    "pips": round(pips, 1),
                })
                current_in = None

    return trades


def parse_report(html_path: str) -> Dict[str, Any]:
    """
    Parses an MT5 Strategy Tester HTML report file and returns a structured dictionary.
    Includes performance metrics, environment metadata, and reconstructed trades.
    """
    if not os.path.exists(html_path):
        raise FileNotFoundError(f"Report file not found: {html_path}")

    content = _read_report_content(html_path)
    if not content or "Total Net Profit" not in content:
        raise ValueError(f"File at {html_path} is not a valid MT5 Strategy Tester report.")

    meta = parse_metadata(content)

    bal_max_money, bal_max_pct = _parse_dd_pair(content, "Balance Drawdown Maximal")
    bal_rel_money, bal_rel_pct = _parse_dd_pair(content, "Balance Drawdown Relative")
    eq_max_money, eq_max_pct = _parse_dd_pair(content, "Equity Drawdown Maximal")
    eq_rel_money, eq_rel_pct = _parse_dd_pair(content, "Equity Drawdown Relative")

    raw_total_trades = _extract_metric_cell(content, "Total Trades")
    raw_total_deals = _extract_metric_cell(content, "Total Deals")

    # History Quality extraction (e.g. History Quality: 100% or 68%)
    history_quality = None
    m_hq = re.search(r"History Quality:\s*</td>\s*<td[^>]*><b>\s*(\d+(?:\.\d+)?)\s*%", content, re.IGNORECASE)
    if m_hq:
        try:
            history_quality = float(m_hq.group(1))
        except ValueError:
            history_quality = None
    else:
        # Fallback to general metric cell extraction if format differs slightly
        raw_hq = _extract_metric_cell(content, "History Quality")
        if raw_hq:
            history_quality = _clean_number(raw_hq)

    metrics: Dict[str, Any] = {
        "file": os.path.abspath(html_path),
        "history_quality": history_quality,
        "total_net_profit": _clean_number(_extract_metric_cell(content, "Total Net Profit")),
        "gross_profit": _clean_number(_extract_metric_cell(content, "Gross Profit")),
        "gross_loss": _clean_number(_extract_metric_cell(content, "Gross Loss")),
        "profit_factor": _clean_number(_extract_metric_cell(content, "Profit Factor")),
        "expected_payoff": _clean_number(_extract_metric_cell(content, "Expected Payoff")),
        "sharpe_ratio": _clean_number(_extract_metric_cell(content, "Sharpe Ratio")),
        "total_trades": int(_clean_number(raw_total_trades) or 0) if raw_total_trades else 0,
        "total_deals": int(_clean_number(raw_total_deals) or 0) if raw_total_deals else 0,
        "margin_level": _clean_number(_extract_metric_cell(content, "Margin Level")),
        "recovery_factor": _clean_number(_extract_metric_cell(content, "Recovery Factor")),
        "balance_drawdown_maximal": {"money": bal_max_money, "pct": bal_max_pct},
        "balance_drawdown_relative": {"money": bal_rel_money, "pct": bal_rel_pct},
        "equity_drawdown_maximal": {"money": eq_max_money, "pct": eq_max_pct},
        "equity_drawdown_relative": {"money": eq_rel_money, "pct": eq_rel_pct},
    }

    trades = parse_trades_and_orders(content, symbol_hint=meta.get("symbol", ""))

    return {
        "metadata": meta,
        "metrics": metrics,
        "trades": trades,
        "generator": "portable-ea5-tester",
    }


def export_trades_csv(trades: List[Dict[str, Any]], output_path: str) -> None:
    """Exports trades list as compact CSV."""
    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    fieldnames = ["id", "t_in", "type", "lot", "p_in", "sl", "tp", "t_out", "p_out", "pnl", "pips"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for t in trades:
            writer.writerow(t)


def generate_batch_summary_html(results: List[Dict[str, Any]], output_path: str) -> str:
    """
    Produces a clean, self-contained, stylish dark-themed HTML report
    comparing all executed tasks (Symbol, Period, Net Profit, Profit Factor, Drawdown, Trades, Win Rate, Detail Report link).
    """
    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    rows_html = []
    total_trades_all = 0
    total_net_pnl_all = 0.0

    for idx, item in enumerate(results, start=1):
        task = item.get("task", {})
        metrics = item.get("parsed", {}).get("metrics", {})
        metadata = item.get("parsed", {}).get("metadata", {})
        trades = item.get("parsed", {}).get("trades", [])
        report_path = item.get("report_path")

        symbol = task.get("symbol") or metadata.get("symbol") or "N/A"
        period = task.get("period") or metadata.get("period") or "N/A"
        expert = task.get("expert") or metadata.get("expert") or "N/A"

        net_profit = metrics.get("total_net_profit")
        pf = metrics.get("profit_factor")
        total_trades = metrics.get("total_trades", len(trades))
        dd = metrics.get("balance_drawdown_maximal", {})
        dd_money = dd.get("money")
        dd_pct = dd.get("pct")
        hq = metrics.get("history_quality")

        min_quality = float(task.get("min_history_quality", 90.0))
        is_low_quality = (hq is not None and hq < min_quality)

        # Check if optimization task
        is_opt = bool(item.get("parsed", {}).get("passes") or int(task.get("optimization", 0)) > 0)
        best_p = item.get("parsed", {}).get("best_pass")
        if is_opt and best_p:
            if net_profit is None and best_p.get("Profit") is not None:
                net_profit = best_p.get("Profit")
            if pf is None and best_p.get("Profit Factor") is not None:
                pf = best_p.get("Profit Factor")
            if total_trades == 0 and best_p.get("Trades") is not None:
                total_trades = int(best_p.get("Trades"))
            if dd_pct is None and best_p.get("Equity DD %") is not None:
                dd_pct = best_p.get("Equity DD %")

        # Win rate computation from reconstructed trades if available
        win_count = sum(1 for t in trades if t.get("pnl", 0) > 0)
        win_rate = (win_count / len(trades) * 100.0) if trades else None

        net_pnl_val = net_profit if net_profit is not None else 0.0
        total_net_pnl_all += net_pnl_val
        total_trades_all += total_trades

        pnl_class = "profit-pos" if net_pnl_val > 0 else ("profit-neg" if net_pnl_val < 0 else "profit-zero")
        pnl_str = f"{net_profit:+.2f}" if net_profit is not None else "N/A"
        pf_str = f"{pf:.2f}" if pf is not None else "N/A"
        dd_str = f"{dd_money:.2f} ({dd_pct:.2f}%)" if (dd_money is not None and dd_pct is not None) else (f"{dd_pct:.2f}%" if dd_pct is not None else (f"{dd_money:.2f}" if dd_money is not None else "N/A"))
        wr_str = f"{win_rate:.1f}%" if win_rate is not None else "N/A"

        if is_opt:
            mode_tag = '<span class="badge" style="background:#388bfd;color:#fff;">OPT</span>'
        else:
            mode_tag = ""

        if hq is not None:
            if is_low_quality:
                hq_html = f'<span class="badge-quality-warn">&#9888; {hq:.1f}% (LOW)</span>'
            else:
                hq_html = f'<span class="badge-quality-ok">{hq:.1f}%</span>'
        else:
            hq_html = '<span class="badge">N/A</span>'

        row_class = ' class="row-warning"' if is_low_quality else ''

        # Prefer html_report_path or html counterpart over raw xml
        display_rep_path = item.get("html_report_path") or report_path
        if display_rep_path and display_rep_path.lower().endswith(".xml"):
            html_cand = os.path.splitext(display_rep_path)[0] + ".html"
            if os.path.exists(html_cand):
                display_rep_path = html_cand

        report_link_html = "N/A"
        if display_rep_path:
            rel_link = os.path.relpath(display_rep_path, os.path.dirname(output_path))
            rel_link = rel_link.replace("\\", "/")
            report_link_html = f'<a href="{rel_link}" target="_blank" class="btn-report">View Report &rarr;</a>'

        row = f"""
        <tr{row_class}>
          <td><span class="badge">#{idx}</span> {mode_tag}</td>
          <td><b>{symbol}</b></td>
          <td><span class="tag">{period}</span></td>
          <td><code>{expert}</code></td>
          <td>{hq_html}</td>
          <td class="{pnl_class} font-bold">{pnl_str}</td>
          <td>{pf_str}</td>
          <td>{dd_str}</td>
          <td>{total_trades}</td>
          <td>{wr_str}</td>
          <td>{report_link_html}</td>
        </tr>"""
        rows_html.append(row)

    total_pnl_class = "profit-pos" if total_net_pnl_all > 0 else ("profit-neg" if total_net_pnl_all < 0 else "profit-zero")

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Portable Strategy Tester - Batch Summary</title>
<style>
  :root {{
    --bg-dark: #0f141c;
    --card-bg: #1a2230;
    --border-color: #2b3648;
    --text-primary: #e6edf3;
    --text-secondary: #8b949e;
    --accent-blue: #388bfd;
    --accent-green: #2ea043;
    --accent-red: #f85149;
    --accent-cyan: #39c5cf;
    --font-stack: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background-color: var(--bg-dark);
    color: var(--text-primary);
    font-family: var(--font-stack);
    padding: 24px;
    line-height: 1.5;
  }}
  .container {{
    max-width: 1200px;
    margin: 0 auto;
  }}
  .header {{
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 20px 24px;
    margin-bottom: 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 16px;
  }}
  .header h1 {{
    font-size: 20px;
    font-weight: 600;
    color: var(--text-primary);
    display: flex;
    align-items: center;
    gap: 10px;
  }}
  .header .meta {{
    font-size: 13px;
    color: var(--text-secondary);
  }}
  .stats-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
  }}
  .stat-card {{
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 16px;
  }}
  .stat-card .label {{
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
    margin-bottom: 6px;
  }}
  .stat-card .value {{
    font-size: 22px;
    font-weight: 700;
    color: var(--text-primary);
  }}
  .table-card {{
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    overflow: hidden;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }}
  th, td {{
    padding: 12px 16px;
    text-align: left;
    border-bottom: 1px solid var(--border-color);
  }}
  th {{
    background: rgba(0, 0, 0, 0.2);
    color: var(--text-secondary);
    font-weight: 600;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.5px;
  }}
  tr:last-child td {{
    border-bottom: none;
  }}
  tr:hover td {{
    background: rgba(255, 255, 255, 0.02);
  }}
  tr.row-warning {{
    background: rgba(255, 184, 108, 0.08);
  }}
  tr.row-warning:hover td {{
    background: rgba(255, 184, 108, 0.12);
  }}
  .badge {{
    background: #21262d;
    border: 1px solid var(--border-color);
    color: var(--text-secondary);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 11px;
  }}
  .badge-quality-ok {{
    background: rgba(46, 160, 67, 0.15);
    border: 1px solid rgba(46, 160, 67, 0.4);
    color: #50fa7b;
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 700;
    font-size: 11px;
    display: inline-block;
  }}
  .badge-quality-warn {{
    background: rgba(255, 85, 85, 0.2);
    border: 1px solid #ff5555;
    color: #ffb86c;
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 700;
    font-size: 11px;
    display: inline-block;
  }}
  .tag {{
    background: rgba(56, 139, 253, 0.15);
    color: var(--accent-blue);
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 600;
    font-size: 12px;
  }}
  code {{
    background: #161b22;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
    font-size: 12px;
    color: var(--accent-cyan);
  }}
  .btn-report {{
    color: #388bfd;
    text-decoration: none;
    padding: 4px 10px;
    background: rgba(56, 139, 253, 0.1);
    border: 1px solid rgba(56, 139, 253, 0.4);
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    display: inline-block;
    transition: all 0.2s;
  }}
  .btn-report:hover {{
    background: rgba(56, 139, 253, 0.25);
    text-decoration: none;
  }}
  .profit-pos {{ color: var(--accent-green); }}
  .profit-neg {{ color: var(--accent-red); }}
  .profit-zero {{ color: var(--text-secondary); }}
  .font-bold {{ font-weight: 700; }}
  .footer {{
    margin-top: 24px;
    text-align: center;
    font-size: 12px;
    color: var(--text-secondary);
  }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <h1>Portable Strategy Tester - Batch Summary</h1>
      <div class="meta">Automated Headless MT5 Strategy Evaluation Report</div>
    </div>
    <div class="meta">Tasks: {len(results)}</div>
  </div>

  <div class="stats-grid">
    <div class="stat-card">
      <div class="label">Total Tasks</div>
      <div class="value">{len(results)}</div>
    </div>
    <div class="stat-card">
      <div class="label">Cumulative Net PnL</div>
      <div class="value {total_pnl_class}">{total_net_pnl_all:+.2f}</div>
    </div>
    <div class="stat-card">
      <div class="label">Total Closed Trades</div>
      <div class="value">{total_trades_all}</div>
    </div>
  </div>

  <div class="table-card">
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Symbol</th>
          <th>Period</th>
          <th>Expert</th>
          <th>History Quality</th>
          <th>Net Profit</th>
          <th>Profit Factor</th>
          <th>Max Balance DD</th>
          <th>Trades</th>
          <th>Win Rate</th>
          <th>Detail Report</th>
        </tr>
      </thead>
      <tbody>
        {"".join(rows_html)}
      </tbody>
    </table>
  </div>

  <div class="footer">
    Generated by portable-ea5-tester &bull; Pure ASCII &amp; Zero External Dependencies
  </div>
</div>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_template)

    return os.path.abspath(output_path)


def format_summary_table(report_dict: Dict[str, Any]) -> str:
    """Formats metrics dictionary into an ASCII Markdown summary table with clean footer."""
    metrics = report_dict.get("metrics", {})
    meta = report_dict.get("metadata", {})

    def _fmt(val, digits=2, suffix=""):
        if val is None:
            return "N/A"
        if isinstance(val, (int, float)):
            return f"{val:.{digits}f}{suffix}"
        return f"{val}{suffix}"

    bal_dd = metrics.get("balance_drawdown_maximal", {})
    bal_dd_str = f"{_fmt(bal_dd.get('money'))} ({_fmt(bal_dd.get('pct'), 2, '%')})"

    hq = metrics.get("history_quality")
    hq_str = _fmt(hq, 1, "%")

    lines = [
        "| Metric | Value |",
        "|:---|:---|",
        f"| Strategy / Expert | `{meta.get('expert', 'N/A')}` |",
        f"| Symbol / Period | {meta.get('symbol', 'N/A')} ({meta.get('period', 'N/A')}) |",
        f"| History Quality | {hq_str} |",
        f"| Total Net Profit | {_fmt(metrics.get('total_net_profit'))} |",
        f"| Profit Factor | {_fmt(metrics.get('profit_factor'))} |",
        f"| Expected Payoff | {_fmt(metrics.get('expected_payoff'))} |",
        f"| Sharpe Ratio | {_fmt(metrics.get('sharpe_ratio'))} |",
        f"| Total Trades | {metrics.get('total_trades', 0)} |",
        f"| Balance DD Maximal | {bal_dd_str} |",
        "",
        "_Generated by portable-ea5-tester_",
    ]
    return "\n".join(lines)


def parse_optimization_xml(file_path: str) -> Dict[str, Any]:
    """
    Parses an MT5 Optimization XML report (XML Spreadsheet 2003 format).
    Extracts column headers, individual optimization passes, parameters, and identifies best pass.
    Standard library ElementTree only. Pure ASCII.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Optimization XML report not found: {file_path}")

    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except Exception as e:
        raise ValueError(f"Failed to parse XML file at {file_path}: {e}")

    ns = {"ss": "urn:schemas-microsoft-com:office:spreadsheet"}
    table = root.find(".//ss:Table", ns)
    if table is None:
        table = root.find(".//Table")
    if table is None:
        # Fallback without namespace
        for elem in root.iter():
            if elem.tag.endswith("Table"):
                table = elem
                break

    if table is None:
        raise ValueError(f"No Table element found in optimization XML: {file_path}")

    # Extract DocumentProperties metadata if available
    metadata: Dict[str, Any] = {}
    for elem in root.iter():
        if elem.tag.endswith("DocumentProperties"):
            for child in elem:
                tag_name = child.tag.split("}")[-1]
                metadata[tag_name] = child.text

    rows = []
    for r in table:
        if r.tag.endswith("Row"):
            rows.append(r)

    if not rows:
        return {
            "metadata": metadata,
            "headers": [],
            "passes": [],
            "passes_count": 0,
            "best_pass": None,
        }

    # Extract headers from first row
    headers: List[str] = []
    first_row = rows[0]
    for cell in first_row:
        if cell.tag.endswith("Cell"):
            data_elem = None
            for child in cell:
                if child.tag.endswith("Data"):
                    data_elem = child
                    break
            val = data_elem.text if data_elem is not None and data_elem.text is not None else ""
            headers.append(val.strip())

    known_metric_cols = {
        "pass", "result", "profit", "expected payoff", "profit factor",
        "recovery factor", "sharpe ratio", "custom", "equity dd %", "trades"
    }

    passes: List[Dict[str, Any]] = []

    for row_elem in rows[1:]:
        cells_data: List[Optional[str]] = []
        for cell in row_elem:
            if cell.tag.endswith("Cell"):
                data_elem = None
                for child in cell:
                    if child.tag.endswith("Data"):
                        data_elem = child
                        break
                val = data_elem.text if data_elem is not None and data_elem.text is not None else ""
                cells_data.append(val.strip())

        if not cells_data or not any(cells_data):
            continue

        pass_dict: Dict[str, Any] = {}
        params_dict: Dict[str, Any] = {}

        for h_idx, h_name in enumerate(headers):
            c_val_str = cells_data[h_idx] if h_idx < len(cells_data) else None
            c_val: Any = _clean_number(c_val_str)
            if c_val is None and c_val_str is not None:
                c_val = c_val_str

            pass_dict[h_name] = c_val
            if h_name.lower() not in known_metric_cols:
                params_dict[h_name] = c_val

        pass_dict["parameters"] = params_dict
        passes.append(pass_dict)

    # Determine best pass (highest Result or Profit)
    best_pass: Optional[Dict[str, Any]] = None
    if passes:
        def _sort_key(p: Dict[str, Any]) -> float:
            r = p.get("Result")
            if r is not None and isinstance(r, (int, float)):
                return float(r)
            prof = p.get("Profit")
            if prof is not None and isinstance(prof, (int, float)):
                return float(prof)
            return -float("inf")

        best_pass = max(passes, key=_sort_key)

    return {
        "metadata": metadata,
        "headers": headers,
        "passes": passes,
        "passes_count": len(passes),
        "best_pass": best_pass,
    }


def generate_optimization_html(xml_path: str, output_html_path: str) -> str:
    """
    Parses MT5 XML optimization spreadsheet and generates a standalone,
    dark-themed HTML optimization dashboard matching batch_summary.html styling.
    Features:
    - Metadata overview (Title, Strategy/Expert, Symbol, Period, Currency, Passes Count).
    - Best Pass highlight card (#1 optimal parameter set with largest Profit/Result).
    - Complete passes table with sorting/styling for Profit, PF, Payoff, DD%, Trades, and Parameters.
    """
    parsed = parse_optimization_xml(xml_path)
    metadata = parsed.get("metadata", {})
    headers = parsed.get("headers", [])
    passes = parsed.get("passes", [])
    best_pass = parsed.get("best_pass")
    passes_count = parsed.get("passes_count", len(passes))

    parent = os.path.dirname(os.path.abspath(output_html_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    title = metadata.get("Title") or "MT5 Optimization Report"
    expert = metadata.get("expert") or metadata.get("Expert") or "N/A"
    symbol = metadata.get("symbol") or metadata.get("Symbol") or "N/A"
    period = metadata.get("period") or metadata.get("Period") or "N/A"
    deposit_str = str(metadata.get("deposit") or metadata.get("Deposit") or "")

    known_metric_cols = {
        "pass", "result", "profit", "expected payoff", "profit factor",
        "recovery factor", "sharpe ratio", "custom", "equity dd %", "trades"
    }
    param_headers = [h for h in headers if h.lower() not in known_metric_cols]
    metric_headers = [h for h in headers if h.lower() in known_metric_cols]

    # Best pass card HTML
    best_pass_html = ""
    if best_pass:
        bp_pass = best_pass.get("Pass", "N/A")
        bp_profit = best_pass.get("Profit")
        bp_pf = best_pass.get("Profit Factor")
        bp_dd = best_pass.get("Equity DD %")
        bp_trades = best_pass.get("Trades")
        bp_payoff = best_pass.get("Expected Payoff")

        profit_str = f"{bp_profit:+.2f}" if isinstance(bp_profit, (int, float)) else str(bp_profit or "N/A")
        profit_cls = "profit-pos" if (isinstance(bp_profit, (int, float)) and bp_profit > 0) else ("profit-neg" if (isinstance(bp_profit, (int, float)) and bp_profit < 0) else "profit-zero")
        pf_str = f"{bp_pf:.2f}" if isinstance(bp_pf, (int, float)) else str(bp_pf or "N/A")
        dd_str = f"{bp_dd:.2f}%" if isinstance(bp_dd, (int, float)) else str(bp_dd or "N/A")
        payoff_str = f"{bp_payoff:.2f}" if isinstance(bp_payoff, (int, float)) else str(bp_payoff or "N/A")
        trades_str = str(bp_trades if bp_trades is not None else "N/A")

        params = best_pass.get("parameters", {})
        param_tags = "".join(f'<span class="tag" style="margin:2px 4px;">{k} = <b>{v}</b></span>' for k, v in params.items())

        best_pass_html = f"""
  <div class="best-card">
    <div class="best-header">
      <span class="badge" style="background:#2ea043;color:#fff;font-size:12px;padding:3px 8px;">BEST PASS #{bp_pass}</span>
      <span style="font-size:14px;color:var(--text-secondary);">Optimal Parameter Set</span>
    </div>
    <div class="stats-grid" style="margin-top:14px;margin-bottom:14px;">
      <div class="stat-card">
        <div class="label">Net Profit</div>
        <div class="value {profit_cls}">{profit_str}</div>
      </div>
      <div class="stat-card">
        <div class="label">Profit Factor</div>
        <div class="value">{pf_str}</div>
      </div>
      <div class="stat-card">
        <div class="label">Equity DD %</div>
        <div class="value">{dd_str}</div>
      </div>
      <div class="stat-card">
        <div class="label">Trades</div>
        <div class="value">{trades_str}</div>
      </div>
      <div class="stat-card">
        <div class="label">Expected Payoff</div>
        <div class="value">{payoff_str}</div>
      </div>
    </div>
    <div style="background:#131922;border:1px solid var(--border-color);border-radius:6px;padding:12px;">
      <div style="font-size:11px;text-transform:uppercase;color:var(--text-secondary);margin-bottom:6px;">Parameters:</div>
      <div>{param_tags if param_tags else "<i>No parameters recorded</i>"}</div>
    </div>
  </div>"""

    # Table rows
    table_headers_html = "".join(f"<th>{h}</th>" for h in headers)
    rows_html = []
    for p in passes:
        is_best = (best_pass is not None and p.get("Pass") == best_pass.get("Pass"))
        row_cls = ' class="best-row"' if is_best else ''
        cells = []
        for h in headers:
            val = p.get(h)
            h_lower = h.lower()
            if h_lower == "pass":
                badge = f'<span class="badge">#{val}</span>'
                if is_best:
                    badge += ' <span class="badge" style="background:#2ea043;color:#fff;">TOP</span>'
                cells.append(f"<td>{badge}</td>")
            elif h_lower in ("profit", "result"):
                if isinstance(val, (int, float)):
                    cls = "profit-pos" if val > 0 else ("profit-neg" if val < 0 else "profit-zero")
                    cells.append(f'<td class="{cls} font-bold">{val:+.2f}</td>')
                else:
                    cells.append(f"<td>{val or 'N/A'}</td>")
            elif h_lower in ("profit factor", "recovery factor", "sharpe ratio", "expected payoff"):
                val_str = f"{val:.2f}" if isinstance(val, (int, float)) else str(val if val is not None else "N/A")
                cells.append(f"<td>{val_str}</td>")
            elif h_lower == "equity dd %":
                val_str = f"{val:.2f}%" if isinstance(val, (int, float)) else str(val if val is not None else "N/A")
                cells.append(f"<td>{val_str}</td>")
            elif h_lower == "trades":
                cells.append(f"<td>{val if val is not None else 'N/A'}</td>")
            else:
                # Parameter or other metric
                if h in param_headers:
                    cells.append(f"<td><code>{val}</code></td>")
                else:
                    cells.append(f"<td>{val if val is not None else ''}</td>")
        rows_html.append(f"<tr{row_cls}>" + "".join(cells) + "</tr>")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} - Optimization Dashboard</title>
<style>
  :root {{
    --bg-dark: #0f141c;
    --card-bg: #1a2230;
    --border-color: #2b3648;
    --text-primary: #e6edf3;
    --text-secondary: #8b949e;
    --accent-blue: #388bfd;
    --accent-green: #2ea043;
    --accent-red: #f85149;
    --accent-cyan: #39c5cf;
    --font-stack: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background-color: var(--bg-dark);
    color: var(--text-primary);
    font-family: var(--font-stack);
    padding: 24px;
    line-height: 1.5;
  }}
  .container {{
    max-width: 1400px;
    margin: 0 auto;
  }}
  .header {{
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 20px 24px;
    margin-bottom: 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 16px;
  }}
  .header h1 {{
    font-size: 20px;
    font-weight: 600;
    color: var(--text-primary);
    display: flex;
    align-items: center;
    gap: 10px;
  }}
  .header .meta {{
    font-size: 13px;
    color: var(--text-secondary);
  }}
  .stats-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
  }}
  .stat-card {{
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 16px;
  }}
  .stat-card .label {{
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
    margin-bottom: 6px;
  }}
  .stat-card .value {{
    font-size: 22px;
    font-weight: 700;
    color: var(--text-primary);
  }}
  .best-card {{
    background: linear-gradient(135deg, rgba(46, 160, 67, 0.08) 0%, rgba(26, 34, 48, 1) 100%);
    border: 1px solid rgba(46, 160, 67, 0.4);
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 24px;
  }}
  .best-header {{
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  .table-card {{
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    overflow-x: auto;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    white-space: nowrap;
  }}
  th, td {{
    padding: 12px 16px;
    text-align: left;
    border-bottom: 1px solid var(--border-color);
  }}
  th {{
    background: rgba(0, 0, 0, 0.2);
    color: var(--text-secondary);
    font-weight: 600;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.5px;
  }}
  tr:last-child td {{
    border-bottom: none;
  }}
  tr:hover td {{
    background: rgba(255, 255, 255, 0.02);
  }}
  tr.best-row {{
    background: rgba(46, 160, 67, 0.1);
  }}
  tr.best-row:hover td {{
    background: rgba(46, 160, 67, 0.15);
  }}
  .badge {{
    background: #21262d;
    border: 1px solid var(--border-color);
    color: var(--text-secondary);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 11px;
    display: inline-block;
  }}
  .tag {{
    background: rgba(56, 139, 253, 0.15);
    color: var(--accent-blue);
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 600;
    font-size: 12px;
    display: inline-block;
  }}
  code {{
    background: #161b22;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
    font-size: 12px;
    color: var(--accent-cyan);
  }}
  .profit-pos {{ color: var(--accent-green); }}
  .profit-neg {{ color: var(--accent-red); }}
  .profit-zero {{ color: var(--text-secondary); }}
  .font-bold {{ font-weight: 700; }}
  .footer {{
    margin-top: 24px;
    text-align: center;
    font-size: 12px;
    color: var(--text-secondary);
  }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <h1>Optimization Dashboard</h1>
      <div class="meta">{title} {f'&bull; {deposit_str}' if deposit_str else ''}</div>
    </div>
    <div class="meta">
      <b>{symbol}</b> &bull; <span class="tag">{period}</span> &bull; <code>{expert}</code>
    </div>
  </div>

  <div class="stats-grid">
    <div class="stat-card">
      <div class="label">Total Passes</div>
      <div class="value">{passes_count}</div>
    </div>
    <div class="stat-card">
      <div class="label">Tested Parameters</div>
      <div class="value">{len(param_headers)}</div>
    </div>
  </div>

  {best_pass_html}

  <div class="table-card">
    <table>
      <thead>
        <tr>
          {table_headers_html}
        </tr>
      </thead>
      <tbody>
        {"".join(rows_html)}
      </tbody>
    </table>
  </div>

  <div class="footer">
    Generated by portable-ea5-tester &bull; MT5 Optimization Suite &bull; Zero External Dependencies
  </div>
</div>
</body>
</html>
"""
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html)

    return os.path.abspath(output_html_path)

