"""
config.py — 所有筛选参数集中在这里管理
调整阈值时只改这一个文件
"""

# ── 赛道（CoinGecko category id）─────────────────────────────────────────────
TARGET_CATEGORIES = [
    "real-world-assets-rwa",
    "artificial-intelligence",
]

# ── 粗筛规则阈值 ──────────────────────────────────────────────────────────────
MC_FDV_MIN          = 0.5
MARKET_CAP_MIN_USD  = 10_000_000    # 最低市值 $10M
MARKET_CAP_MAX_USD  = 500_000_000   # 最高市值 $500M

# ── 社交热度阈值（CoinGecko 综合评分）────────────────────────────────────────
SOCIAL_SCORE_MIN    = 0.0           # 调低阈值，让更多真实项目通过

# ── 过滤关键词（名称包含这些词的币种直接排除）────────────────────────────────
EXCLUDE_NAME_KEYWORDS = [
    "bStocks Tokenized Stock",  # 代币化股票，不是加密原生项目
    "Tokenized Stock",
    "bStocks",
]

# ── LunarCrush 阈值（付费后启用）─────────────────────────────────────────────
LUNAR_SOCIAL_SCORE_MIN   = 0
LUNAR_SOCIAL_CHANGE_MIN  = 20

# ── 输出设置 ──────────────────────────────────────────────────────────────────
MAX_CANDIDATES = 20
REPORT_TITLE   = "🔍 加密潜力币每日筛选报告"
