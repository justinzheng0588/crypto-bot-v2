"""
data_sources.py — 所有外部 API 调用集中在这里

社交数据源优先级：
1. LunarCrush（付费，高质量，暂时停用）
2. CoinGecko community_data（免费，当前使用）
3. Santiment（备选，中等价位）
4. CryptoPanic（备选，免费，适合叙事校验）
"""

import os
import time
import requests

COINGECKO_BASE   = "https://api.coingecko.com/api/v3"
BINANCE_BASE     = "https://api.binance.com/api/v3"
LUNARCRUSH_BASE  = "https://lunarcrush.com/api4/public"

COINGECKO_API_KEY  = os.environ.get("COINGECKO_API_KEY", "")
LUNARCRUSH_API_KEY = os.environ.get("LUNARCRUSH_API_KEY", "")


def _cg_headers():
    h = {"accept": "application/json"}
    if COINGECKO_API_KEY:
        h["x-cg-demo-api-key"] = COINGECKO_API_KEY
    return h


# ── CoinGecko 行情数据 ────────────────────────────────────────────────────────

def get_category_coins(category_id: str, per_page: int = 100) -> list:
    url = f"{COINGECKO_BASE}/coins/markets"
    params = {
        "vs_currency": "usd",
        "category": category_id,
        "order": "market_cap_desc",
        "per_page": per_page,
        "page": 1,
        "sparkline": False,
    }
    resp = requests.get(url, params=params, headers=_cg_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


# ── CoinGecko 社交数据（免费，当前使用）──────────────────────────────────────

def get_cg_social_data(coin_id: str) -> dict | None:
    """
    从 CoinGecko 获取单个币种的社交数据
    返回: {
        "twitter_followers": int,
        "reddit_active_users": int,
        "telegram_channel_user_count": int,
        "social_score": float,  # 综合评分（我们自己计算）
        "social_score_change_24h": float  # 暂时无法从CG获取变化率，返回0
    }
    """
    url = f"{COINGECKO_BASE}/coins/{coin_id}"
    params = {
        "localization": False,
        "tickers": False,
        "market_data": False,
        "community_data": True,
        "developer_data": False,
    }
    try:
        resp = requests.get(url, params=params, headers=_cg_headers(), timeout=10)
        if not resp.ok:
            return None
        data = resp.json()
        community = data.get("community_data") or {}

        twitter    = community.get("twitter_followers") or 0
        reddit     = community.get("reddit_active_users") or 0
        telegram   = community.get("telegram_channel_user_count") or 0

        # 综合社交评分：加权求和（Twitter权重最高）
        # 用对数压缩避免大数字主导
        import math
        score = (
            math.log10(twitter + 1) * 3 +
            math.log10(reddit + 1) * 2 +
            math.log10(telegram + 1) * 1
        )

        return {
            "twitter_followers": twitter,
            "reddit_active_users": reddit,
            "telegram_channel_user_count": telegram,
            "social_score": round(score, 2),
            "social_score_change_24h": 0,  # CoinGecko 不提供24h变化率
        }
    except Exception:
        return None


def get_cg_social_batch(coin_id_map: dict, delay: float = 0.5) -> dict:
    """
    批量获取多个币种的 CoinGecko 社交数据
    coin_id_map: {symbol: coingecko_id}，比如 {"INJ": "injective-protocol"}
    返回: {symbol: social_data}
    """
    results = {}
    total = len(coin_id_map)
    for i, (symbol, coin_id) in enumerate(coin_id_map.items(), 1):
        if i % 10 == 0:
            print(f"   社交数据进度: {i}/{total}...")
        data = get_cg_social_data(coin_id)
        if data and data["social_score"] > 0:
            results[symbol.upper()] = data
        time.sleep(delay)
    return results


# ── Binance 公开 API（不需要 Key）────────────────────────────────────────────

_binance_symbols: set | None = None

def get_binance_listed_symbols() -> set:
    global _binance_symbols
    if _binance_symbols is not None:
        return _binance_symbols
    url = f"{BINANCE_BASE}/exchangeInfo"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    symbols = set()
    for s in data.get("symbols", []):
        if s.get("status") == "TRADING" and s.get("quoteAsset") == "USDT":
            symbols.add(s["baseAsset"].upper())
    _binance_symbols = symbols
    return symbols


def is_on_binance(symbol: str) -> bool:
    return symbol.upper() in get_binance_listed_symbols()


# ── LunarCrush（保留接口，付费后可直接启用）──────────────────────────────────

def get_lunar_social_data(symbol: str) -> dict | None:
    """
    LunarCrush 社交数据（需要付费订阅 Individual 或以上）
    当前暂停使用，接口保留供以后升级
    """
    if not LUNARCRUSH_API_KEY:
        return None
    url = f"{LUNARCRUSH_BASE}/coins/{symbol.lower()}/v1"
    headers = {"Authorization": f"Bearer {LUNARCRUSH_API_KEY}"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if not resp.ok:
            return None
        data = resp.json().get("data") or {}
        if isinstance(data, list):
            data = data[0] if data else {}
        return {
            "social_score": data.get("social_score", 0) or 0,
            "social_score_change_24h": data.get("social_score_change_24h", 0) or 0,
        }
    except Exception:
        return None


def get_lunar_batch(symbols: list, delay: float = 0.3) -> dict:
    """LunarCrush 批量查询（付费后启用）"""
    results = {}
    for symbol in symbols:
        data = get_lunar_social_data(symbol)
        if data and data.get("social_score", 0) > 0:
            results[symbol.upper()] = data
        time.sleep(delay)
    return results


# ── 统一社交数据接口（切换数据源只改这里）────────────────────────────────────

SOCIAL_SOURCE = "coingecko"  # 可选: "coingecko" | "lunarcrush"

def get_social_batch(candidates: list, delay: float = 0.5) -> dict:
    """
    统一社交数据获取入口
    candidates: 基础筛选后的候选列表，每个元素含 symbol 和 coingecko_id
    切换数据源只需改 SOCIAL_SOURCE 变量
    """
    if SOCIAL_SOURCE == "lunarcrush":
        symbols = [c["symbol"] for c in candidates]
        return get_lunar_batch(symbols, delay)
    else:
        # 默认使用 CoinGecko
        coin_id_map = {c["symbol"]: c["coingecko_id"] for c in candidates if c.get("coingecko_id")}
        return get_cg_social_batch(coin_id_map, delay)
