# 竞彩足球数据面板 — 配置

DATABASE_PATH = "data/dashboard.db"

# 爬虫配置
SCRAPER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)
SCRAPER_TIMEOUT = 15
SCRAPER_RETRY = 3
SCRAPER_DELAY = 2  # 请求间隔（秒）

# 稳健策略默认参数
DEFAULT_PRINCIPAL = 200.0       # 默认本金
DEFAULT_BET_RATIO = 0.05        # 每次投注5%
DEFAULT_STOP_LOSS = 0.15        # 亏损15%止损
DEFAULT_TAKE_PROFIT = 0.30      # 盈利30%止盈
DEFAULT_ODDS_MIN = 1.6          # 推荐赔率下限
DEFAULT_ODDS_MAX = 2.0          # 推荐赔率上限
DEFAULT_WEEKLY_LIMIT = 3        # 每周最多投注次数

# 3串4 策略参数
COMBO_3X4_ODDS_MIN = 1.7
COMBO_3X4_ODDS_MAX = 2.2

# 赔率异常检测阈值
ODDS_ANOMALY_THRESHOLD = 0.2    # 两源赔率差>0.2视为异常

# 支持的玩法（用户选定）
PLAY_TYPES = ["spf", "rspf", "score"]
PLAY_TYPE_NAMES = {
    "spf": "胜平负",
    "rspf": "让球胜平负",
    "score": "比分"
}
