"""
配置参数模块
Configuration parameters for the CB quantitative selection system
"""

# ============ 筛选参数 Selection Parameters ============
# 最大转股溢价率(%)，超过此值的债券将被过滤
MAX_PREMIUM_RATE = 50.0

# 最小到期收益率(%)，低于此值的债券将被过滤
MIN_YTM = -10.0

# 最小日成交额(万元)，用于流动性过滤
MIN_DAILY_VOLUME = 100.0

# 最大价格，超过此价格的债券风险较高
MAX_PRICE = 150.0

# 最小价格，低于此价格可能有特殊风险
MIN_PRICE = 90.0

# 输出前N只债券
TOP_N = 30

# ============ 评分权重 Scoring Weights ============
# 各因子在综合评分中的权重，总和应为1
WEIGHTS = {
    'premium_rate': 0.35,      # 转股溢价率权重（越低越好）
    'ytm': 0.25,               # 到期收益率权重（越高越好）
    'double_low': 0.25,        # 双低值权重（越低越好）
    'convert_value': 0.15,     # 转股价值权重（越高越好）
}

# ============ 双低策略参数 Double-Low Strategy ============
# 双低值 = 价格 + 转股溢价率 * 系数
DOUBLE_LOW_COEFFICIENT = 1.0

# ============ 风险过滤 Risk Filters ============
# 是否过滤ST股票对应的转债
FILTER_ST = True

# 是否过滤已公告强赎的转债
FILTER_FORCED_REDEMPTION = True

# 剩余规模最小值(亿元)，规模太小流动性差
MIN_OUTSTANDING = 0.5

# ============ 输出设置 Output Settings ============
# 默认输出文件名
DEFAULT_OUTPUT_FILE = "cb_selection_result.csv"

# 显示的小数位数
DECIMAL_PLACES = 2

# ============ 数据源设置 Data Source Settings ============
# 请求超时时间(秒)
REQUEST_TIMEOUT = 30

# 请求重试次数
MAX_RETRIES = 3

# 重试间隔(秒)
RETRY_INTERVAL = 2
