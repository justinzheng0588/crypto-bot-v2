"""
screener.py — 筛选逻辑，分两步
Step 1: run_screener_basic  — 市值 + MC/FDV + Binance上线 + 排除黑名单
Step 2: run_screener_social — 叠加社交热度
"""

from config import (
    MC_FDV_MIN,
    MARKET_CAP_MIN_USD,
    MARKET_CAP_MAX_USD,
    SOCIAL_SCORE_MIN,
    EXCLUDE_NAME_KEYWORDS,
)


def check_market_cap(coin: dict) -> tuple[bool, str]:
    mc = coin.get("market_cap") or 0
    if mc < MARKET_CAP_MIN_USD:
        return False, f"市值过低 ${mc:,.0f}"
    if mc > MARKET_CAP_MAX_USD:
        return False, f"市值过高 ${mc:,.0f}"
    return True, f"市值 ${mc:,.0f}"


def check_mc_fdv_ratio(coin: dict) -> tuple[bool, str]:
    mc  = coin.get("market_cap") or 0
    fdv = coin.get("fully_diluted_valuation") or 0
    if fdv == 0:
        return False, "FDV 数据缺失"
    ratio = mc / fdv
    if ratio < MC_FDV_MIN:
        return False, f"MC/FDV={ratio:.2f} 低于 {MC_FDV_MIN}"
    return True, f"MC/FDV={ratio:.2f}"


def check_binance_listed(coin: dict, binance_symbols: set) -> tuple[bool, str]:
    symbol = (coin.get("symbol") or "").upper()
    if symbol in binance_symbols:
        return True, f"已上 Binance ({symbol}/USDT)"
    return False, f"未上 Binance ({symbol})"


def check_not_excluded(coin: dict) -> tuple[bool, str]:
    """过滤代币化股票等非加密原生项目"""
    name = coin.get("name", "")
    for keyword in EXCLUDE_NAME_KEYWORDS:
        if keyword.lower() in name.lower():
            return False, f"已排除: 名称含 '{keyword}'"
    return True, "通过排除检查"


def check_social_score(social_data: dict | None) -> tuple[bool, str]:
    if social_data is None:
        return True, "社交数据不可用（跳过）"
    score = social_data.get("social_score", 0)
    twitter = social_data.get("twitter_followers", 0)
    if score < SOCIAL_SCORE_MIN:
        return False, f"社交评分过低 (score={score:.1f})"
    return True, f"社交评分={score:.1f} Twitter={twitter:,}"


def run_screener_basic(coins: list, binance_symbols: set) -> list:
    """第一步：市值 + MC/FDV + Binance + 排除黑名单"""
    candidates = []
    for coin in coins:
        r0, m0 = check_not_excluded(coin)
        r1, m1 = check_market_cap(coin)
        r2, m2 = check_mc_fdv_ratio(coin)
        r3, m3 = check_binance_listed(coin, binance_symbols)

        if r0 and r1 and r2 and r3:
            mc  = coin.get("market_cap") or 0
            fdv = coin.get("fully_diluted_valuation") or 1
            candidates.append({
                "symbol":        (coin.get("symbol") or "").upper(),
                "name":          coin.get("name", ""),
                "coingecko_id":  coin.get("id", ""),
                "category":      coin.get("_category", ""),
                "price":         coin.get("current_price", 0),
                "change_24h":    coin.get("price_change_percentage_24h", 0),
                "market_cap":    mc,
                "mc_fdv_ratio":  mc / fdv if fdv else 0,
                "social_score":  "N/A",
                "social_change_24h": "N/A",
                "twitter_followers": 0,
                "reasons": {
                    "排除检查":   m0,
                    "市值范围":   m1,
                    "MC/FDV比":   m2,
                    "Binance上线": m3,
                },
            })
    return candidates


def run_screener_social(basic_candidates: list, social_batch: dict) -> list:
    """第二步：叠加社交热度过滤"""
    if not social_batch:
        print("   ⚠️  无社交数据，跳过社交热度过滤（返回全部基础候选）")
        return basic_candidates

    candidates = []
    for c in basic_candidates:
        social_data = social_batch.get(c["symbol"])
        passed, reason = check_social_score(social_data)
        if passed:
            if social_data:
                c["social_score"] = social_data.get("social_score", "N/A")
                c["twitter_followers"] = social_data.get("twitter_followers", 0)
            c["reasons"]["社交热度"] = reason
            candidates.append(c)
    return candidates
