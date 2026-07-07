"""
main.py — 主入口
运行顺序：
1. CoinGecko 按赛道拉取候选池
2. Binance 公开 API 获取上线列表
3. 基础粗筛（市值 + MC/FDV + Binance）
4. 只对候选币获取社交数据（CoinGecko，免费）
5. 叠加社交热度过滤
6. 输出到 Telegram + 本地 HTML
"""

import os
import sys

from config import TARGET_CATEGORIES, MAX_CANDIDATES, REPORT_TITLE
from data_sources import get_category_coins, get_binance_listed_symbols, get_social_batch
from screener import run_screener_basic, run_screener_social
from reporter import (
    build_telegram_message, send_telegram,
    build_html_report, save_html_report,
)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")


def main():
    print("=" * 60)
    print("🚀 Crypto Screener 启动")
    print("=" * 60)

    # ── Step 1: 按赛道拉取候选池 ──────────────────────────────────────────
    all_coins = []
    for cat_id in TARGET_CATEGORIES:
        cat_name = cat_id.replace("-", " ").title()
        print(f"\n📡 CoinGecko: 拉取赛道 [{cat_name}]...")
        try:
            coins = get_category_coins(cat_id)
            print(f"   → 获取 {len(coins)} 个币种")
            for c in coins:
                c["_category"] = cat_name
            all_coins.extend(coins)
        except Exception as e:
            print(f"   ⚠️  获取失败: {e}", file=sys.stderr)

    # 去重
    seen = set()
    unique_coins = []
    for c in all_coins:
        if c["id"] not in seen:
            seen.add(c["id"])
            unique_coins.append(c)
    print(f"\n✅ 去重后共 {len(unique_coins)} 个候选币种")

    # ── Step 2: Binance 上线列表 ───────────────────────────────────────────
    print("\n📡 Binance: 获取现货上线列表...")
    try:
        binance_symbols = get_binance_listed_symbols()
        print(f"   → 共 {len(binance_symbols)} 个 USDT 交易对")
    except Exception as e:
        print(f"   ⚠️  获取失败: {e}", file=sys.stderr)
        binance_symbols = set()

    # ── Step 3: 基础筛选 ───────────────────────────────────────────────────
    print("\n🔍 第一步筛选（市值 + MC/FDV + Binance上线）...")
    basic_candidates = run_screener_basic(unique_coins, binance_symbols)
    print(f"   → 基础筛选后剩余: {len(basic_candidates)} 个币种")

    # ── Step 4: 只对候选币获取社交数据 ────────────────────────────────────
    print(f"\n📡 社交数据: 只查询 {len(basic_candidates)} 个基础候选币种...")
    try:
        social_batch = get_social_batch(basic_candidates)
        print(f"   → 成功获取 {len(social_batch)} 个币种的社交数据")
    except Exception as e:
        print(f"   ⚠️  获取失败: {e}", file=sys.stderr)
        social_batch = {}

    # ── Step 5: 叠加社交热度过滤 ──────────────────────────────────────────
    print("\n🔍 第二步筛选（叠加社交热度）...")
    candidates = run_screener_social(basic_candidates, social_batch)
    candidates.sort(key=lambda x: x["market_cap"], reverse=True)
    candidates = candidates[:MAX_CANDIDATES]
    print(f"   → 最终候选: {len(candidates)} 个币种")
    for c in candidates:
        print(f"      • {c['symbol']:10s} {c['name']}")

    # ── Step 6: 输出 ──────────────────────────────────────────────────────
    message = build_telegram_message(candidates, REPORT_TITLE)
    print("\n" + "─" * 60)
    print("📨 Telegram 消息预览:")
    print("─" * 60)
    print(message)

    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            send_telegram(message, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
            print("\n✅ Telegram 发送成功")
        except Exception as e:
            print(f"\n❌ Telegram 发送失败: {e}", file=sys.stderr)
    else:
        print("\n⚠️  未配置 Telegram 凭据，跳过发送（仅本地预览）")

    html = build_html_report(candidates, REPORT_TITLE)
    html_path = save_html_report(html, output_dir=".")
    print(f"✅ HTML 报告已保存: {html_path}")
    print("\n🏁 完成")


if __name__ == "__main__":
    main()
