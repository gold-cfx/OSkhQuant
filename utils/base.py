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


def detect_sideways_breakout(df):
    """
    选择横盘突破的股票
    输入是一个DataFrame，包含open, high, low, close, volume列
    输出是一个Series，标记是否为突破日
    """
    high_20 = df['high'].rolling(20).max()
    low_20 = df['low'].rolling(20).min()
    range_20 = high_20 - low_20
    range_pct = range_20 / low_20

    ma_vol_20 = df['volume'].rolling(20).mean()
    is_narrow = range_pct <= 0.05
    is_breakout = (df['close'] > df['open']) & \
                  (df['close'] > high_20.shift(1)) & \
                  (df['volume'] > 1.5 * ma_vol_20)

    signal = is_narrow.shift(1) & is_breakout
    return signal


def calculate_future_returns(df, signal, days=20):
    """
     计算每个信号后N日的收益
     """
    future_returns = []
    signal_dates = df[signal].index

    for date in signal_dates:
        try:
            entry_price = df.loc[date, 'close']
            future_data = df.loc[date:].iloc[1:days + 1]  # 排除买入当天
            max_return = (future_data['close'] - entry_price) / entry_price
            final_return = (future_data.iloc[-1]['close'] - entry_price) / entry_price
            future_returns.append({
                'date': date,
                'final_return': final_return,
                'max_return': max_return.max()
            })
        except:
            continue

    return pd.DataFrame(future_returns)


def is_limit_up(row, price_col="close", limit_col="limitUp", tol=0.001):
    """
    判断是否涨停（收盘价接近涨停价）
    :param row: DataFrame 单行
    :param price_col: 收盘价列名
    :param limit_col: 涨停价列名
    :param tol: 容差，默认0.1%（考虑四舍五入和撮合差异）
    """
    price = row[price_col]
    limit_price = row[limit_col]
    return abs(price - limit_price) / limit_price <= tol


def is_relative_low(df, idx, window=60, ratio=0.7):
    """
    判断是否相对低位
    :param df: 股票日线数据
    :param idx: 涨停日索引
    :param window: 回溯窗口，比如60日
    :param ratio: 相对低位比例，比如0.7表示低于60日高点70%
    """
    if idx < window:
        return True  # 数据不足时默认放行
    recent_high = df.iloc[idx - window:idx]["high"].max()
    price = df.iloc[idx]["close"]
    return price <= recent_high * ratio


def is_volume_up(row, df, idx, window=5):
    """判断是否放量（成交量大于前N日均量）"""
    if idx < window:
        return False
    avg_vol = df.iloc[idx - window:idx]["volume"].mean()
    return row["volume"] > avg_vol


def is_doji(row, tol=0.005):
    """判断是否标准十字星（开盘≈收盘，且有上下影线）"""
    body = abs(row["close"] - row["open"])
    mid = (row["close"] + row["open"]) / 2
    cond_body = body / mid <= tol
    cond_shadow = row["high"] > max(row["open"], row["close"]) and row["low"] < min(row["open"], row["close"])
    return cond_body and cond_shadow


def check_consolidation2(df, start_idx, base_price, days=7):
    """判断横盘震荡（不破涨停一半，缩量，横盘>=7天）"""
    sub = df.iloc[start_idx:start_idx + days]
    if len(sub) < days:
        return False

    # 条件1：收盘价不破涨停板1/2
    if (sub["close"] < base_price).any():
        return False

    # 条件2：成交量逐步缩量
    return sub["volume"].mean() < df.iloc[start_idx - 3:start_idx]["volume"].mean()


def check_consolidation(df, start_idx, base_price, days=7, ref_high=None, tol=0.01):
    """
    判断横盘震荡
    条件：
    1. 收盘价不破涨停板1/2
    2. 横盘期间成交量缩量
    3. 横盘最高价不超过参考高点1%（十字星或涨停板高点）
    :param df: DataFrame
    :param start_idx: 横盘起始位置（十字星之后）
    :param base_price: 涨停板实体1/2价格
    :param days: 横盘要求的最少天数
    :param ref_high: 参考高点（一般取十字星或涨停板的最高价）
    :param tol: 容差比例，比如0.01表示允许1%突破
    """
    sub = df.iloc[start_idx:start_idx + days]
    if len(sub) < days:
        return False

    # 条件1：收盘价不破涨停板1/2
    if (sub["close"] < base_price).any():
        return False

    # 条件2：成交量缩量
    if sub["volume"].mean() >= df.iloc[start_idx - 3:start_idx]["volume"].mean():
        return False

    # 条件3：最高价不超过参考高点 * (1 + tol)
    if ref_high is not None:
        if sub["high"].max() > ref_high * (1 + tol):
            return False

    return True


def is_st(code):
    """判断是否ST股"""
    data = xtdata.get_instrument_detail(code)
    name = data['InstrumentName']
    if "st" in name.lower() or "*" in name:
        return True
    return False


def find_strategy_signals(df, lookback=60):
    """
    查找满足“涨停十字星战法”的信号
    """
    signals = []
    if len(df) < lookback:
        return signals
    for i in range(len(df) - lookback, len(df) - 10):  # 至少留足空间
        base_price = None
        today = df.iloc[i]
        tomorrow = df.iloc[i + 1]

        # 条件1：低位放量涨停
        # 处于最近1年低位的股票
        window = 250
        if i < window:
            continue
        if not is_relative_low(df, i, window=window, ratio=0.7):
            continue
        if not is_limit_up(today, 'close', 'limitUp'):
            continue
        if not is_volume_up(today, df, i):
            continue

        # 条件2：次日标准十字星
        base_price = (today["open"] + today["close"]) / 2  # 涨停板实体中点

        # 条件2：次日标准十字星，且没有跳空缺口
        if tomorrow["low"] > today["high"] or tomorrow["high"] < today["low"]:
            continue  # 出现跳空，直接跳过

        # 十字星
        if not is_doji(tomorrow):
            continue

        #  在涨停1/2之上
        if tomorrow["close"] < base_price:
            continue

        # 条件3：横盘震荡 + 缩量
        ref_high = max(today["high"], tomorrow["high"])
        if not check_consolidation(df, i + 2, base_price, days=7, ref_high=ref_high):
            continue

        # 条件4：突破 突破之前也要在涨停1/2之上
        cons_end = i + 2 + 7
        for j in range(cons_end, min(cons_end + 60, len(df))):  # 最多观察60天突破
            # 检查突破前的所有收盘价是否都在 base_price 之上
            if (df.iloc[cons_end:j]["close"] < base_price).any():
                continue
            if df.iloc[j]["close"] > tomorrow["high"] and df.iloc[j]["volume"] > df.iloc[j - 5:j]["volume"].mean():
                st = is_st(df.iloc[j]["code"])
                if not st:  # 排除ST股
                    signals.append({
                        "date": df.iloc[j]["date"],
                        "signal_price": df.iloc[j]["close"]
                    })
                break
    return signals
