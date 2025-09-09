from khQuantImport import *


def calc_annual_volatility(price_list):
    # 计算对数收益率
    log_returns = np.log(price_list[1:] / price_list[:-1])

    # 计算30天日波动率
    daily_volatility = np.std(log_returns, ddof=1)

    # 年化波动率
    annual_volatility = daily_volatility * np.sqrt(252)
    return annual_volatility


def determine_trend(prices, window=20):
    if len(prices) < window:
        raise ValueError("数据不足")

    recent_prices = prices[-window:]
    highs = pd.Series(recent_prices).rolling(5).max().dropna()
    lows = pd.Series(recent_prices).rolling(5).min().dropna()

    # 1. 判断上升趋势：创新高次数多，线性回归斜率为正
    increasing_highs = np.sum(np.diff(highs) > 0) / len(highs)
    slope = np.polyfit(range(len(recent_prices)), recent_prices, 1)[0]

    # 2. 判断下降趋势：创新低次数多，线性回归斜率为负
    decreasing_lows = np.sum(np.diff(lows) < 0) / len(lows)

    # 3. 判断震荡趋势：高低点方差小，斜率接近0
    high_std = np.std(highs)
    low_std = np.std(lows)
    avg_std = (high_std + low_std) / 2

    # 综合判断逻辑
    if increasing_highs > 0.6 and slope > 0:
        return "上升趋势", 1
    elif decreasing_lows > 0.6 and slope < 0:
        return "下降趋势", -1
    elif avg_std < 0.5 * np.mean(recent_prices) and abs(slope) < 0.1:
        return "震荡趋势", 0
    else:
        return "趋势不明", -10


def calc_three_high_low(c: pd.Series, h: pd.Series, l: pd.Series):
    """
    三高三低指标（向量化版）
    参数
    ----
    c : pd.Series  收盘价序列
    h : pd.Series  最高价序列
    l : pd.Series  最低价序列

    返回
    ----
    up   : pd.Series(bool)  非“三低”标记序列
    down : pd.Series(bool)  非“三高”标记序列
    """
    # 前 1 根 K 线
    pre_c = c.shift(1)
    pre_h = h.shift(1)
    pre_l = l.shift(1)

    # 三低：收盘、最高、最低全部低于前 2 根对应值
    all_lt = (c < pre_c) & (h < pre_h) & (l < pre_l)
    # 三高：收盘、最高、最低全部高于前 2 根对应值
    all_gt = (c > pre_c) & (h > pre_h) & (l > pre_l)

    # 非三低 => up；非三高 => down
    up = ~all_lt
    down = ~all_gt

    return pd.Series(up), pd.Series(down)


def calc_trend(up: pd.Series, down: pd.Series, c: pd.Series, n=5):
    count_high = COUNT(up, n)
    count_low = COUNT(down, n)
    ratio_high = count_high / n
    ratio_low = count_low / n
    slope1 = SLOPE(c, n)
    up_trend = (ratio_high > 0.6) & (slope1 > 0)
    down_trend = (ratio_low > 0.6) & (slope1 < 0)
    shake_trend = ~up_trend & ~down_trend

    return pd.Series(up_trend), pd.Series(down_trend), pd.Series(shake_trend)
