from khQuantImport import *


def calc_annual_volatility(price_list):
    # 计算对数收益率
    log_returns = np.log(price_list[1:] / price_list[:-1])

    # 计算30天日波动率
    daily_volatility = np.std(log_returns, ddof=1)

    # 年化波动率
    annual_volatility = daily_volatility * np.sqrt(252)
    return annual_volatility


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
    """
    通过三不高的分布来判断趋势
    """
    count_high = COUNT(up, n)
    count_low = COUNT(down, n)
    ratio_high = count_high / n
    ratio_low = count_low / n
    slope1 = SLOPE(c, n)
    up_trend = (ratio_high > 0.6) & (slope1 > 0)
    down_trend = (ratio_low > 0.6) & (slope1 < 0)
    shake_trend = ~up_trend & ~down_trend

    return pd.Series(up_trend), pd.Series(down_trend), pd.Series(shake_trend)
