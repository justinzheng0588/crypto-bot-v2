"""
reporter.py — 输出格式化
1. Telegram 消息（纯文本）
2. 本地 HTML 报告
"""

import os
from datetime import datetime, timezone, timedelta

NZ_TZ = timezone(timedelta(hours=12))


def _nz_now() -> str:
    return datetime.now(NZ_TZ).strftime("%Y-%m-%d %H:%M NZST")


def _fmt_mcap(usd: float) -> str:
    if usd >= 1_000_000_000:
        return f"${usd/1_000_000_000:.2f}B"
    if usd >= 1_000_000:
        return f"${usd/1_000_000:.1f}M"
    return f"${usd:,.0f}"


def _fmt_twitter(n) -> str:
    if not isinstance(n, (int, float)) or n == 0:
        return "N/A"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.0f}K"
    return str(n)


# ── Telegram ──────────────────────────────────────────────────────────────────

def build_telegram_message(candidates: list, title: str) -> str:
    now = _nz_now()
    lines = [f"🔍 {title}", f"📅 {now}", ""]

    if not candidates:
        lines.append("⚠️ 本次扫描未发现符合条件的候选币种。")
        return "\n".join(lines)

    lines.append(f"共发现 {len(candidates)} 个候选币种：")
    lines.append("─" * 30)

    for i, c in enumerate(candidates, 1):
        change = c.get("change_24h") or 0
        score  = c.get("social_score", "N/A")
        score_str = f"{score:.1f}" if isinstance(score, float) else str(score)
        twitter_str = _fmt_twitter(c.get("twitter_followers", 0))

        lines += [
            f"{i}. {c['name']} ({c['symbol']})",
            f"   赛道: {c['category']}",
            f"   价格: ${c['price']:,.4f}  ({change:+.2f}% 24h)",
            f"   市值: {_fmt_mcap(c['market_cap'])}  |  MC/FDV: {c['mc_fdv_ratio']:.2f}",
            f"   社交评分: {score_str}  Twitter: {twitter_str}",
            "",
        ]

    lines.append("数据来源: CoinGecko · Binance")
    lines.append("仅供参考，不构成投资建议。")
    return "\n".join(lines)


def send_telegram(message: str, bot_token: str, chat_id: str) -> None:
    import requests
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    resp = requests.post(url, json=payload, timeout=15)
    resp.raise_for_status()


# ── HTML 报告 ──────────────────────────────────────────────────────────────────

def build_html_report(candidates: list, title: str) -> str:
    now = _nz_now()
    rows = ""

    if not candidates:
        rows = '<tr><td colspan="7" style="text-align:center;color:#888">本次扫描未发现符合条件的候选币种</td></tr>'
    else:
        for i, c in enumerate(candidates, 1):
            change = c.get("change_24h") or 0
            change_color = "#16a34a" if change >= 0 else "#dc2626"
            score = c.get("social_score", "N/A")
            score_str = f"{score:.1f}" if isinstance(score, float) else str(score)
            twitter_str = _fmt_twitter(c.get("twitter_followers", 0))

            rows += f"""
            <tr>
                <td>{i}</td>
                <td><strong>{c['name']}</strong><br><span class="sym">{c['symbol']}</span></td>
                <td>{c['category']}</td>
                <td>${c['price']:,.4f}</td>
                <td style="color:{change_color}">{change:+.2f}%</td>
                <td>{_fmt_mcap(c['market_cap'])}<br><span class="sub">MC/FDV: {c['mc_fdv_ratio']:.2f}</span></td>
                <td>{score_str}<br><span class="sub">Twitter: {twitter_str}</span></td>
            </tr>"""

    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          background: #f8fafc; color: #1e293b; margin: 0; padding: 20px; }}
  .container {{ max-width: 960px; margin: 0 auto; }}
  h1 {{ font-size: 1.4rem; color: #1e3a5f; margin-bottom: 4px; }}
  .meta {{ color: #64748b; font-size: 0.85rem; margin-bottom: 20px; }}
  table {{ width: 100%; border-collapse: collapse; background: white;
           border-radius: 8px; overflow: hidden;
           box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  th {{ background: #1e3a5f; color: white; padding: 10px 12px;
        text-align: left; font-size: 0.85rem; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #f1f5f9; font-size: 0.9rem; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #f8fafc; }}
  .sym {{ color: #64748b; font-size: 0.78rem; }}
  .sub {{ color: #94a3b8; font-size: 0.78rem; }}
  .footer {{ margin-top: 16px; color: #94a3b8; font-size: 0.78rem; text-align: center; }}
</style>
</head>
<body>
<div class="container">
  <h1>🔍 {title}</h1>
  <div class="meta">生成时间: {now} &nbsp;|&nbsp; 候选数量: {len(candidates)}</div>
  <table>
    <thead>
      <tr>
        <th>#</th><th>币种</th><th>赛道</th><th>价格</th>
        <th>24h涨跌</th><th>市值</th><th>社交评分</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
  <div class="footer">数据来源: CoinGecko · Binance &nbsp;|&nbsp; 仅供参考，不构成投资建议</div>
</div>
</body>
</html>"""


def save_html_report(html: str, output_dir: str = ".") -> str:
    date_str = datetime.now(NZ_TZ).strftime("%Y%m%d")
    filename = f"daily_report_{date_str}.html"
    path = os.path.join(output_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path
